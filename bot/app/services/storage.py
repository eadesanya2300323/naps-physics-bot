from typing import Protocol
from urllib.parse import quote

import httpx


class StorageError(RuntimeError):
    pass


class Storage(Protocol):
    async def put(self, path: str, data: bytes, content_type: str) -> None: ...

    async def get(self, path: str) -> bytes: ...

    async def signed_url(self, path: str, expires_in: int = 60) -> str: ...

    async def delete(self, path: str) -> None: ...


class SupabaseStorage:
    def __init__(
        self,
        base_url: str,
        service_key: str,
        bucket: str,
        client: httpx.AsyncClient | None = None,
    ):
        self._base = base_url.rstrip("/")
        self._key = service_key
        self._bucket = bucket
        self._client = client or httpx.AsyncClient(timeout=60)
        self._owns_client = client is None

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._key}", "apikey": self._key}

    def _object_url(self, path: str) -> str:
        return f"{self._base}/storage/v1/object/{self._bucket}/{quote(path)}"

    def _sign_url(self, path: str) -> str:
        return f"{self._base}/storage/v1/object/sign/{self._bucket}/{quote(path)}"

    def _check(self, response: httpx.Response, action: str) -> None:
        if response.status_code >= 400:
            raise StorageError(f"{action} failed with status {response.status_code}")

    async def put(self, path: str, data: bytes, content_type: str) -> None:
        response = await self._client.put(
            self._object_url(path),
            content=data,
            headers={**self._headers, "Content-Type": content_type, "x-upsert": "true"},
        )
        self._check(response, "Upload")

    async def get(self, path: str) -> bytes:
        response = await self._client.get(self._object_url(path), headers=self._headers)
        self._check(response, "Download")
        return response.content

    async def signed_url(self, path: str, expires_in: int = 60) -> str:
        response = await self._client.post(
            self._sign_url(path),
            json={"expiresIn": expires_in},
            headers=self._headers,
        )
        self._check(response, "Signing")
        relative = response.json().get("signedURL")
        if not relative:
            raise StorageError("Signing returned no URL")
        return f"{self._base}/storage/v1{relative}"

    async def delete(self, path: str) -> None:
        response = await self._client.delete(self._object_url(path), headers=self._headers)
        self._check(response, "Delete")

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()
