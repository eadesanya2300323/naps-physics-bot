ROLES = ("super", "moderator", "uploader")

CAPABILITIES = {
    "materials": ("super", "uploader"),
    "courses": ("super", "uploader"),
    "opportunities": ("super", "uploader"),
    "fyp": ("super", "uploader"),
    "events": ("super", "uploader"),
    "broadcasts": ("super", "moderator"),
    "moderation": ("super", "moderator"),
    "tutors": ("super", "moderator"),
    "maintenance": ("super",),
    "admins": ("super",),
    "backup": ("super",),
    "ownership": ("super",),
}

STUDENT_COMMANDS = ("start", "browse", "search", "pq", "notify", "help")

ADMIN_COMMANDS = (
    "start",
    "browse",
    "search",
    "pq",
    "notify",
    "help",
    "addcourse",
    "addadmin",
    "rmadmin",
    "admins",
    "ban",
    "unban",
    "mute",
    "maintenance",
    "backup",
    "transferowner",
)


def can(role: str | None, capability: str) -> bool:
    if role is None:
        return False
    return role in CAPABILITIES.get(capability, ())


def is_admin(role: str | None) -> bool:
    return role in ROLES
