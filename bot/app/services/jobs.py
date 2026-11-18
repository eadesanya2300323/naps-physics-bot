import asyncio

from aiogram.exceptions import TelegramForbiddenError

from app.keyboards import notification_keyboard
from app.services.job_progress import JobProgress, advance
from app.services.telegram import send_text

CLAIM_JOB = """
update broadcast_jobs
set status = 'sending', updated_at = now()
where id = (
  select id from broadcast_jobs
  where status = 'queued' or (status = 'sending' and updated_at < now() - interval '60 seconds')
  order by id
  limit 1
  for update skip locked
)
returning id, kind, audience, level, message, ref, sent_count, failed_count, last_student_id
"""

NEXT_BATCH = """
select id, telegram_id from students
where telegram_id is not null
  and active
  and not banned
  and ($1 = 'all' or level = $2)
  and ($3 <> 'alert' or notify_uploads)
  and ($4::uuid is null or id > $4::uuid)
order by id
limit $5
"""

SAVE_PROGRESS = """
update broadcast_jobs
set sent_count = $2, failed_count = $3, last_student_id = $4::uuid, updated_at = now()
where id = $1
"""


async def enqueue(db, kind: str, audience: str, message: str, level: str | None = None, ref: str | None = None) -> int:
    return await db.fetchval(
        "insert into broadcast_jobs (kind, audience, level, message, ref) values ($1, $2, $3, $4, $5) returning id",
        kind,
        audience,
        level,
        message,
        ref,
    )


async def process(db, bot, max_jobs: int = 2, batch_size: int = 25, batches_per_job: int = 4) -> dict:
    totals = {"jobs": 0, "sent": 0, "failed": 0}
    for _ in range(max_jobs):
        job = await db.fetchrow(CLAIM_JOB)
        if job is None:
            break
        totals["jobs"] += 1
        progress = JobProgress(
            job["sent_count"],
            job["failed_count"],
            str(job["last_student_id"]) if job["last_student_id"] else None,
            "sending",
        )
        finished = False

        for _ in range(batches_per_job):
            students = await db.fetch(
                NEXT_BATCH,
                job["audience"],
                job["level"],
                job["kind"],
                progress.cursor,
                batch_size,
            )
            if not students:
                finished = True
                progress = advance(progress, [], False)
                break

            results = await asyncio.gather(
                *(send_to_student(bot, db, row, job) for row in students),
                return_exceptions=True,
            )
            outcomes = [
                (str(row["id"]), result is True)
                for row, result in zip(students, results, strict=False)
            ]
            more = len(students) == batch_size
            progress = advance(progress, outcomes, more)
            await db.execute(SAVE_PROGRESS, job["id"], progress.sent, progress.failed, progress.cursor)
            if not more:
                finished = True
                progress = advance(progress, [], False)
                break
            await asyncio.sleep(1)

        await db.execute(
            "update broadcast_jobs set status = $2, updated_at = now(), last_student_id = $3::uuid where id = $1",
            job["id"],
            "sent" if finished else "sending",
            progress.cursor,
        )
        totals["sent"] += progress.sent - job["sent_count"]
        totals["failed"] += progress.failed - job["failed_count"]

    return totals


async def send_to_student(bot, db, row, job) -> bool:
    marker = int(job["ref"]) if job["ref"] and job["ref"].isdigit() else None
    markup = notification_keyboard(marker) if marker else None
    try:
        message = await send_text(bot, row["telegram_id"], job["message"], markup)
    except TelegramForbiddenError:
        await db.execute("update students set active = false where id = $1", row["id"])
        return False
    return message is not None
