from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.caption import CATEGORY_LABELS, CATEGORY_ORDER
from app.services.permissions import can, is_admin

PAGE_SIZE = 8
LEVELS = ("100", "200", "300", "400")


def shorten(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def button(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def back_button(data: str = "home") -> InlineKeyboardButton:
    return button("Back", data)


def home_row() -> list[InlineKeyboardButton]:
    return [button("Home", "home")]


def home_keyboard(role: str | None, notify: bool = True) -> InlineKeyboardMarkup:
    rows = [
        [button("Browse materials", "browse"), button("Search", "searchhelp")],
        [button("My library", "lib:1"), button("Recent", "rec:1")],
        [button("Offline pack", "pack")],
        [button("Opportunities", "opps:all:1"), button("Templates", "tpl:1")],
        [button("Project topics", "fypmenu"), button("Events", "events")],
        [button("Feedback", "feedback")],
    ]
    if is_admin(role):
        rows.append([button("Upload a file", "uploadhelp"), button("Admin commands", "admhelp")])
        if can(role, "moderation"):
            rows.append([button("Inbox", "inbox:1")])
    rows.append([button("Alerts on" if notify else "Alerts off", "ntf")])
    rows.append([button("Help", "helptext")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def level_keyboard(current: str | None = None, prefix: str = "lvl") -> InlineKeyboardMarkup:
    labels = (("100", "100L"), ("200", "200L"), ("300", "300L"), ("400", "400L"))
    buttons = [
        button(f"{label}{' ✓' if value == current else ''}", f"{prefix}:{value}")
        for value, label in labels
    ]
    rows = [buttons[0:2], buttons[2:4], home_row()]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def pager_row(prefix: str, page: int, pages: int) -> list[InlineKeyboardButton]:
    if pages <= 1:
        return []
    items = []
    if page > 1:
        items.append(button("Previous", f"{prefix}:{page - 1}"))
    if page < pages:
        items.append(button("Next", f"{prefix}:{page + 1}"))
    return items


def course_keyboard(courses, level: str, page: int, pages: int) -> InlineKeyboardMarkup:
    rows = [
        [button(f"{course['code']} · {shorten(course['title'], 32)}", f"cat:{level}:{course['code']}")]
        for course in courses
    ]
    pager = pager_row(f"crs:{level}", page, pages)
    if pager:
        rows.append(pager)
    rows.append([back_button("browse"), *home_row()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def category_keyboard(level: str, code: str) -> InlineKeyboardMarkup:
    buttons = [
        button(CATEGORY_LABELS[key], f"ml:{level}:{code}:{key}:-:-:-:1")
        for key in CATEGORY_ORDER
    ]
    rows = [buttons[index : index + 2] for index in range(0, len(buttons), 2)]
    rows.append([back_button(f"crs:{level}:1"), *home_row()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def materials_keyboard(items, page: int, pages: int, prefix: str, level: str, code: str, category: str) -> InlineKeyboardMarkup:
    rows = []
    for offset, item in enumerate(items, start=1):
        number = (page - 1) * PAGE_SIZE + offset
        if item["is_current"]:
            label = f"{number}. {item['year'] or 'n.d.'} · {shorten(item['title'], 28)}"
        else:
            label = f"{number}. {shorten(item['title'], 25)} · outdated"
        rows.append([button(label, f"mat:{item['id']}")])
    pager = pager_row(prefix, page, pages)
    if pager:
        rows.append(pager)
    rows.append([button("Lecturer", f"lec:{level}:{code}:{category}"), back_button(f"cat:{level}:{code}")])
    rows.append(home_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def lecturer_keyboard(level: str, code: str, category: str, lecturers) -> InlineKeyboardMarkup:
    rows = [
        [button(shorten(name, 40), f"lcp:{level}:{code}:{category}:{index}")]
        for index, name in enumerate(lecturers)
    ]
    rows.append([button("All lecturers", f"ml:{level}:{code}:{category}:-:-:-:1")])
    rows.append([back_button(f"ml:{level}:{code}:{category}:-:-:-:1"), *home_row()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def material_keyboard(material: dict, site_url: str, saved: bool, back_label: str, back_data: str) -> InlineKeyboardMarkup:
    rows = [
        [
            button("Saved" if saved else "Save", f"fav:{material['id']}"),
            button("Report", f"report:{material['id']}"),
        ]
    ]
    if site_url and material.get("course_code"):
        rows.append([InlineKeyboardButton(text="Open on website", url=f"{site_url}/material/{material['id']}")])
    rows.append([button(back_label, back_data), *home_row()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def search_keyboard(items, page: int, pages: int, keyword: str) -> InlineKeyboardMarkup:
    rows = []
    for offset, item in enumerate(items, start=1):
        number = (page - 1) * PAGE_SIZE + offset
        label = f"{number}. {item['course_code'] or 'General'} · {shorten(item['title'], 24)}"
        rows.append([button(label, f"mat:{item['id']}")])
    pager = pager_row(f"sr:{keyword}", page, pages)
    if pager:
        rows.append(pager)
    rows.append([button("Browse", "browse"), *home_row()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def notification_keyboard(material_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[button("Open file", f"mat:{material_id}")], [button("Alerts off", "ntf")]]
    )


def saved_keyboard(items, page: int, pages: int, prefix: str) -> InlineKeyboardMarkup:
    rows = []
    for offset, item in enumerate(items, start=1):
        number = (page - 1) * PAGE_SIZE + offset
        label = f"{number}. {item['course_code'] or 'General'} · {shorten(item['title'], 24)}"
        rows.append([button(label, f"mat:{item['id']}")])
    pager = pager_row(prefix, page, pages)
    if pager:
        rows.append(pager)
    rows.append([button("Browse", "browse"), *home_row()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def pack_level_keyboard() -> InlineKeyboardMarkup:
    labels = (("100", "100L"), ("200", "200L"), ("300", "300L"), ("400", "400L"))
    buttons = [button(label, f"pkl:{value}") for value, label in labels]
    rows = [buttons[0:2], buttons[2:4], home_row()]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def pack_confirm_keyboard(level: str, total: int) -> InlineKeyboardMarkup:
    if total == 0:
        return InlineKeyboardMarkup(inline_keyboard=[home_row()])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [button(f"Send {total} files", f"pkgo:{level}")],
            home_row(),
        ]
    )


def opportunity_list_keyboard(rows_data, page: int, pages: int, kind: str | None) -> InlineKeyboardMarkup:
    rows = []
    for item in rows_data:
        label = shorten(item["title"], 30)
        if item["deadline"]:
            label = f"{label} · {item['deadline'].strftime('%d %b')}"
        rows.append([button(label, f"opp:{item['id']}")])
    rows.append([button("All", "opps:all:1"), button("Internships", "opps:internship:1")])
    rows.append([button("Scholarships", "opps:scholarship:1"), button("SIWES", "opps:siwes:1")])
    rows.append([button("Competitions", "opps:competition:1")])
    pager = pager_row(f"opps:{kind or 'all'}", page, pages)
    if pager:
        rows.append(pager)
    rows.append(home_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def opportunity_detail_keyboard(opportunity, can_manage: bool) -> InlineKeyboardMarkup:
    rows = []
    if opportunity["url"]:
        rows.append([InlineKeyboardButton(text="Open link", url=opportunity["url"])])
    if can_manage:
        rows.append([button("Edit", f"oppedit:{opportunity['id']}"), button("Archive", f"oparchive:{opportunity['id']}")])
    rows.append([button("Back", f"opps:{opportunity['kind']}:1"), *home_row()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def opportunity_edit_keyboard(opportunity) -> InlineKeyboardMarkup:
    fields = ("title", "organisation", "deadline", "levels", "url", "description")
    buttons = [button(field.title(), f"oedit:{opportunity['id']}:{field}") for field in fields]
    rows = [buttons[index : index + 2] for index in range(0, len(buttons), 2)]
    rows.append([back_button(f"opp:{opportunity['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def opportunity_kind_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        button(label, f"ochoose:{value}")
        for value, label in (
            ("internship", "Internship"),
            ("scholarship", "Scholarship"),
            ("siwes", "SIWES"),
            ("competition", "Competition"),
            ("other", "Other"),
        )
    ]
    rows = [buttons[index : index + 2] for index in range(0, len(buttons), 2)]
    rows.append([button("Cancel", "home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def opportunity_notify_keyboard(identifier: int) -> InlineKeyboardMarkup:
    rows = [
        [button("100L", f"opush:{identifier}:100"), button("200L", f"opush:{identifier}:200")],
        [button("300L", f"opush:{identifier}:300"), button("400L", f"opush:{identifier}:400")],
        [button("Skip", "home")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def templates_keyboard(items, page: int, pages: int) -> InlineKeyboardMarkup:
    rows = []
    for offset, item in enumerate(items, start=1):
        number = (page - 1) * PAGE_SIZE + offset
        rows.append([button(f"{number}. {shorten(item['title'], 30)}", f"mat:{item['id']}")])
    pager = pager_row("tpl", page, pages)
    if pager:
        rows.append(pager)
    rows.append([button("Browse", "browse"), *home_row()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def fyp_menu_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [button("Available", "fyp:available:0:0:0:1"), button("Taken", "fyp:taken:0:0:0:1")],
        [button("Completed", "fyp:completed:0:0:0:1")],
        [button("By supervisor", "fyps:available"), button("By area", "fypa:available:0")],
        [button("By year", "fypy:available:0:0")],
        home_row(),
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def fyp_list_keyboard(items, page: int, pages: int, prefix: str) -> InlineKeyboardMarkup:
    rows = [
        [button(f"{index}. {shorten(item['title'], 34)}", f"fypitem:{item['id']}")]
        for index, item in enumerate(items, start=1)
    ]
    pager = pager_row(prefix, page, pages)
    if pager:
        rows.append(pager)
    rows.append([button("Filters", "fypmenu"), *home_row()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def fyp_choice_keyboard(values, prefix: str, back: str) -> InlineKeyboardMarkup:
    rows = [
        [button(shorten(str(value), 36), f"{prefix}:{index}")]
        for index, value in enumerate(values)
    ]
    rows.append([back_button(back)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def fyp_detail_keyboard(topic, can_manage: bool) -> InlineKeyboardMarkup:
    rows = []
    if can_manage:
        rows.append([button("Available", f"fypst:{topic['id']}:available"), button("Taken", f"fypst:{topic['id']}:taken")])
        rows.append([button("Completed", f"fypst:{topic['id']}:completed"), button("Remove", f"fypdrop:{topic['id']}")])
    rows.append([button("Back", "fyp:available:0:0:0:1"), *home_row()])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def feedback_kind_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [button("Idea", "fbk:suggestion"), button("Bot problem", "fbk:bug")],
        [button("Something else", "fbk:other")],
        home_row(),
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def inbox_keyboard(entries, page: int, pages: int) -> InlineKeyboardMarkup:
    rows = []
    for offset, entry in enumerate(entries, start=1):
        number = (page - 1) * PAGE_SIZE + offset
        body = " ".join(entry["body"].split())[:24]
        rows.append([button(f"{number}. {entry['status']} · {body}", f"fb:{entry['id']}")])
    pager = pager_row("inbox", page, pages)
    if pager:
        rows.append(pager)
    rows.append(home_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def inbox_detail_keyboard(entry) -> InlineKeyboardMarkup:
    rows = [
        [button("Mark read", f"fbset:{entry['id']}:read"), button("Resolved", f"fbset:{entry['id']}:resolved")],
    ]
    if entry["material_id"]:
        rows.append([button("Remove file", f"fbfile:{entry['id']}")])
        rows.append([button("Open file", f"mat:{entry['material_id']}")])
    rows.append([back_button("inbox:1")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def events_keyboard(events, is_admin: bool, active: bool) -> InlineKeyboardMarkup:
    rows = []
    for event in events:
        row = [InlineKeyboardButton(text=shorten(event["title"], 28), url=event["url"])]
        if is_admin:
            row.append(button("Turn off" if active else "Turn on", f"{'evoff' if active else 'evon'}:{event['id']}"))
        rows.append(row)
    if is_admin:
        rows.append([button("Inactive links" if active else "Active links", "evin" if active else "events")])
    rows.append(home_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def year_keyboard() -> InlineKeyboardMarkup:
    years = list(range(2026, 2015, -1))
    buttons = [button(str(year), f"up:yr:{year}") for year in years]
    rows = [buttons[index : index + 4] for index in range(0, len(buttons), 4)]
    rows.append([button("No year", "up:yr:-")])
    rows.append([button("Cancel upload", "up:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def semester_keyboard() -> InlineKeyboardMarkup:
    rows = [[button("Semester 1", "up:sem:1"), button("Semester 2", "up:sem:2")]]
    rows.append([button("No semester", "up:sem:-")])
    rows.append([button("Cancel upload", "up:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def upload_lecturer_keyboard(names) -> InlineKeyboardMarkup:
    buttons = [button(shorten(name, 30), f"up:lec:{index}") for index, name in enumerate(names)]
    rows = [buttons[index : index + 2] for index in range(0, len(buttons), 2)]
    rows.append([button("New lecturer", "up:lecnew"), button("Skip", "up:lecskip")])
    rows.append([button("Cancel upload", "up:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def upload_category_keyboard(code: str | None) -> InlineKeyboardMarkup:
    buttons = [button(CATEGORY_LABELS[key], f"up:cat:{key}") for key in CATEGORY_ORDER]
    rows = [buttons[index : index + 2] for index in range(0, len(buttons), 2)]
    rows.append([button("Cancel upload", "up:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def upload_courses_keyboard(courses, page: int, pages: int) -> InlineKeyboardMarkup:
    rows = [[button("Template, no course", "up:tpl")]]
    rows.extend(
        [button(f"{course['code']} · {shorten(course['title'], 30)}", f"up:code:{course['code']}")]
        for course in courses
    )
    pager = pager_row("up:crs", page, pages)
    if pager:
        rows.append(pager)
    rows.append([button("Cancel upload", "up:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def skip_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[button("Skip", f"{prefix}:skip")], [button("Cancel", "home")]]
    )


def confirm_keyboard(prefix: str, value: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [button("Confirm", f"{prefix}:yes:{value}")],
            [button("Cancel", f"{prefix}:no:{value}")],
        ]
    )
