from datetime import date
from html import escape

from app.services.caption import CATEGORY_LABELS
from app.services.feedback import KIND_LABELS as FEEDBACK_LABELS
from app.services.feedback import status_label as feedback_status
from app.services.fyp import status_label as fyp_status
from app.services.opportunities import KIND_LABELS, close_label, level_label
from app.services.opportunities import KIND_LABELS as OPPORTUNITY_LABELS


def course_label(code: str, title: str | None = None) -> str:
    if title:
        return f"{escape(code)} · {escape(title)}"
    return escape(code)


def welcome() -> str:
    return (
        "<b>NAPS Physics Library</b>\n"
        "Past questions, notes and lab templates for Covenant University physics students.\n\n"
        "Tell me your level and I will keep the library filtered to it."
    )


def home() -> str:
    return (
        "<b>Physics Library</b>\n"
        "Browse by course, search a title, or open your saved files."
    )


def level_prompt() -> str:
    return "<b>Your level</b>\nPick one. You can change it with /start."


def courses_prompt(level: str, total: int) -> str:
    if total == 0:
        return f"<b>{level}L</b>\nNo courses on file for this level yet. An admin can add them with /addcourse."
    return f"<b>{level}L courses</b>\n{total} on file. Tap a course to see what it has."


def categories_prompt(code: str, title: str) -> str:
    return f"<b>{course_label(code, title)}</b>\nChoose a category."


def listing_prompt(
    code: str,
    category: str,
    total: int,
    page: int,
    pages: int,
    year=None,
    semester=None,
    lecturer=None,
) -> str:
    lines = [f"<b>{escape(code)} · {CATEGORY_LABELS[category]}</b>"]
    lines.append(f"{total} files · page {page} of {pages}")
    filters = []
    if year:
        filters.append(f"Year {year}")
    if semester:
        filters.append(f"Semester {semester}")
    if lecturer:
        filters.append(escape(lecturer))
    if filters:
        lines.append(" · ".join(filters))
    return "\n".join(lines)


def empty_listing(code: str, category: str) -> str:
    return f"No {CATEGORY_LABELS[category].lower()} for {escape(code)} yet."


def lecturer_prompt(code: str, category: str, total: int) -> str:
    if total == 0:
        return f"No lecturers recorded for {escape(code)} {CATEGORY_LABELS[category].lower()} yet."
    return f"<b>Filter by lecturer</b>\n{total} recorded for {escape(code)} {CATEGORY_LABELS[category].lower()}."


def material_caption(material: dict) -> str:
    lines = [f"<b>{escape(material['title'])}</b>"]
    details = [escape(material["course_code"] or "General"), CATEGORY_LABELS[material["category"]]]
    if material.get("year"):
        details.append(str(material["year"]))
    if material.get("semester"):
        details.append(f"Semester {material['semester']}")
    lines.append(" · ".join(details))
    status = "Current" if material["is_current"] else "Outdated"
    if material["version"] > 1:
        status = f"{status} · version {material['version']}"
    lines.append(status)
    if material.get("lecturer"):
        lines.append(f"Lecturer: {escape(material['lecturer'])}")
    return "\n".join(lines)


def large_file(title: str, size_mb: int) -> str:
    return (
        f"<b>{escape(title)}</b>\n"
        f"This file is {size_mb} MB, above the 50 MB Telegram limit. "
        "Open it on the library site instead."
    )


def file_unavailable() -> str:
    return "That file could not be read from storage. Try again in a minute."


def search_prompt() -> str:
    return "Send a course code or a word from a title after /search, like /search optics."


def search_prompt_short() -> str:
    return "Send /search followed by a course code or a word from a title, like /search PHY201."


def search_results(keyword: str, total: int, page: int, pages: int) -> str:
    if total == 0:
        return f"Nothing matched “{escape(keyword)}”. Try a course code like PHY201."
    return f"<b>Results for “{escape(keyword)}”</b>\n{total} files · page {page} of {pages}"


def pq_usage() -> str:
    return "Send /pq with a course code, and optionally a year or semester, like /pq PHY201 2023 sem2."


def course_missing(code: str) -> str:
    return f"{escape(code)} is not in the course list yet. An admin can add it with /addcourse."


def notify_on() -> str:
    return "Alerts are on. I will message you when files land for your level."


def notify_off() -> str:
    return "Alerts are off. Switch them back on with /notify."


def help_text() -> str:
    return (
        "<b>Student commands</b>\n"
        "/start · pick your level\n"
        "/browse · level, course, category\n"
        "/search &lt;word&gt; · find by code or title\n"
        "/pq PHY201 2023 · past questions by code and year\n"
        "/library · files you saved\n"
        "/recent · files you opened last\n"
        "/pack 200L · key files for a level\n"
        "/opportunities · internships and scholarships\n"
        "/templates · lab report and project templates\n"
        "/fyp · final year project topics\n"
        "/events · merch and ticket links\n"
        "/feedback · tell the admins something\n"
        "/notify · switch new-file alerts\n"
        "/help · this list"
    )


def admin_help_text(role: str) -> str:
    return (
        "<b>Admin commands</b>\n"
        f"Your role: {role}\n\n"
        "/addcourse PHY201 | Optics | 200 | 1\n"
        "/addopportunity · guided post, then push to a level\n"
        "/delopportunity &lt;id&gt; · /addfyp Supervisor | Title | Year | Area\n"
        "/fypstatus &lt;id&gt; available|taken|completed · /rmfyp &lt;id&gt;\n"
        "/addevent Title | URL | YYYY-MM-DD | Description · /rmevent &lt;id&gt;\n"
        "/inbox · feedback and file reports\n"
        "/delmaterial &lt;id&gt; · remove a file and its stored copy\n"
        "/admins · /addadmin &lt;id&gt; &lt;role&gt; · /rmadmin &lt;id&gt;\n"
        "/ban &lt;id&gt; · /unban &lt;id&gt; · /mute &lt;id&gt; &lt;minutes&gt;\n"
        "/maintenance &lt;message&gt; or /maintenance off · /backup · /transferowner &lt;id&gt;\n\n"
        "Send a file with the caption CODE | category | title | year | semester | lecturer, or send it alone for a guided upload."
    )


def upload_prompt() -> str:
    return (
        "<b>Upload a file</b>\n"
        "Send the file with a caption:\n"
        "<code>PHY201 | pq | First semester past questions | 2023 | 1 | Dr Okafor</code>\n"
        "Send it without a caption and I will ask for each field."
    )


def upload_choose_course() -> str:
    return "<b>Which course?</b>\nTap the course for this file, or choose a template with no course."


def upload_choose_category(code: str) -> str:
    return f"<b>{escape(code)}</b>\nWhich category is the file?"


def upload_ask_title(code: str | None, category: str) -> str:
    if code is None:
        return f"<b>Template</b>\nSend a title, like Lab report template."
    return (
        f"<b>{escape(code)} · {CATEGORY_LABELS[category]}</b>\n"
        "Send a title, like First semester past questions."
    )


def upload_ask_year(title: str) -> str:
    return f"<b>{escape(title)}</b>\nWhich year?"


def upload_ask_semester(title: str) -> str:
    return f"<b>{escape(title)}</b>\nWhich semester?"


def upload_ask_lecturer(code: str | None, total: int) -> str:
    label = escape(code) if code else "Template"
    if total == 0:
        return f"<b>{label}</b>\nNo lecturers recorded yet. Send a name, or tap Skip."
    return f"<b>{label}</b>\nPick the lecturer, add a new one, or tap Skip."


def upload_ask_lecturer_typed(code: str) -> str:
    return f"<b>{escape(code)}</b>\nSend the lecturer's name."


def upload_done(code: str | None, category: str, title: str, version: int, superseded: int) -> str:
    label = escape(code) if code else "Templates"
    lines = ["<b>File added</b>", f"{escape(title)}", f"{label} · {CATEGORY_LABELS[category]} · version {version}"]
    if superseded:
        lines.append(f"{superseded} older version marked outdated.")
    return "\n".join(lines)


def duplicate_file(title: str) -> str:
    return f"That file is already in the library as “{escape(title)}”."


def upload_too_large(size_mb: int) -> str:
    return f"Telegram lets bots download files up to 20 MB, and this one is {size_mb} MB. Use the dashboard upload for it."


def caption_format() -> str:
    return "Caption format: CODE | category | title | year | semester | lecturer"


def upload_reset() -> str:
    return "Upload cancelled."


def course_added(code: str, title: str, level: str) -> str:
    return f"Added {course_label(code, title)} to {level}L."


def course_updated(code: str, title: str, level: str) -> str:
    return f"Updated {course_label(code, title)} at {level}L."


def admin_added(telegram_id: int, role: str) -> str:
    return f"{telegram_id} is now {role}."


def admin_removed(telegram_id: int) -> str:
    return f"{telegram_id} no longer has admin access."


def owner_protected() -> str:
    return "The owner cannot be removed."


def admin_list(rows) -> str:
    if not rows:
        return "No admins on file."
    lines = ["<b>Admins</b>"]
    lines.extend(f"{row['telegram_id']} · {row['role']}" for row in rows)
    return "\n".join(lines)


def student_banned(telegram_id: str) -> str:
    return f"{escape(str(telegram_id))} is banned."


def student_unbanned(telegram_id: str) -> str:
    return f"{escape(str(telegram_id))} can use the bot again."


def student_muted(telegram_id: str, minutes: int) -> str:
    return f"{escape(str(telegram_id))} is muted for {minutes} minutes."


def student_missing() -> str:
    return "No student with that Telegram id yet."


def maintenance_set(message: str) -> str:
    return f"Maintenance mode on.\n“{escape(message)}”"


def maintenance_off() -> str:
    return "Maintenance mode off."


def maintenance_notice(message: str) -> str:
    return f"{escape(message)}\n\nThe library is paused for a moment. Try again later."


def owner_transfer_prompt(telegram_id: str) -> str:
    return f"Make {escape(str(telegram_id))} the owner? That role cannot be removed later."


def owner_transferred(telegram_id: int) -> str:
    return f"{telegram_id} is now the owner."


def owner_transfer_cancelled() -> str:
    return "Owner transfer cancelled."


def library_header(total: int, page: int, pages: int) -> str:
    if total == 0:
        return "<b>My library</b>\nNothing saved yet. Tap Save on any file to keep it here."
    return f"<b>My library</b>\n{total} saved · page {page} of {pages}"


def recent_header(total: int, page: int, pages: int) -> str:
    if total == 0:
        return "<b>Recent files</b>\nNothing opened yet. Files you open will show up here."
    return f"<b>Recent files</b>\n{total} opened · page {page} of {pages}"


def saved_on() -> str:
    return "Saved to your library."


def saved_off() -> str:
    return "Removed from your library."


def pack_prompt() -> str:
    return "Send /pack with a level, like /pack 200L, to get the key files for that level."


def pack_confirm(level: str, total: int) -> str:
    if total == 0:
        return f"<b>{level}L pack</b>\nNo key files for this level yet. An admin marks files as key."
    return (
        f"<b>{level}L pack</b>\n"
        f"{total} key files, sent one at a time.\n"
        "This can take a minute on a slow connection."
    )


def pack_progress(done: int, total: int) -> str:
    return f"Sending {done} of {total}"


def pack_done(done: int) -> str:
    return f"Pack finished. {done} files sent."


def pack_failed() -> str:
    return "The pack stopped early. Try /pack again."


def opportunity_header(kind: str | None, total: int, page: int, pages: int) -> str:
    label = KIND_LABELS[kind] if kind else "Opportunities"
    if total == 0:
        return f"<b>{label}</b>\nNothing open right now. Admins post new items here."
    return f"<b>{label}</b>\n{total} open · page {page} of {pages}"


def opportunity_body(opportunity, today: date) -> str:
    lines = [f"<b>{escape(opportunity['title'])}</b>"]
    if opportunity["organisation"]:
        lines.append(escape(opportunity["organisation"]))
    lines.append(close_label(opportunity["deadline"]))
    lines.append(level_label(opportunity["levels"]))
    if opportunity["description"]:
        lines.append("")
        lines.append(escape(opportunity["description"]))
    return "\n".join(lines)


def opportunity_button(opportunity) -> str:
    label = opportunity["title"][:30]
    if opportunity["deadline"]:
        return f"{label} · {opportunity['deadline'].strftime('%d %b')}"
    return label


def opportunity_kind_prompt() -> str:
    return "<b>New opportunity</b>\nWhich kind?"


def opportunity_title_prompt() -> str:
    return "<b>New opportunity</b>\nSend a title, like NNPC undergraduate scholarship."


def opportunity_organisation_prompt() -> str:
    return "Send the organisation, or tap Skip."


def opportunity_deadline_prompt() -> str:
    return "Send the deadline as 2026-11-30, or tap Skip."


def opportunity_levels_prompt() -> str:
    return "Send the levels it is for, like 200 300, or tap Skip for all levels."


def opportunity_url_prompt() -> str:
    return "Send the application link, or tap Skip."


def opportunity_description_prompt() -> str:
    return "Send a short description, or tap Skip."


def opportunity_saved(identifier: int) -> str:
    return f"Opportunity {identifier} saved. Push it to a level if students should hear about it now."


def opportunity_edit_prompt(field: str, current: str | None) -> str:
    shown = escape(current) if current else "empty"
    return f"<b>{escape(field.title())}</b>\nNow: {shown}\nSend the new value, or tap Cancel."


def opportunity_archived() -> str:
    return "Opportunity archived. Students will not see it."


def opportunity_removed() -> str:
    return "Opportunity removed."


def opportunity_pushed(level: str) -> str:
    return f"Queued for {level}L students. It goes out on the next tick."


def opportunity_missing() -> str:
    return "That opportunity is gone."


def template_header(total: int, page: int, pages: int) -> str:
    if total == 0:
        return "<b>Templates</b>\nNo lab report or project templates yet."
    return f"<b>Templates</b>\n{total} on file · page {page} of {pages}"


def fyp_header(status: str, total: int, page: int, pages: int, filters: str = "") -> str:
    lines = [f"<b>Project topics · {fyp_status(status)}</b>"]
    if total == 0:
        lines.append("Nothing here yet. Try another filter.")
        return "\n".join(lines)
    lines.append(f"{total} topics · page {page} of {pages}")
    if filters:
        lines.append(filters)
    return "\n".join(lines)


def fyp_body(topic) -> str:
    lines = [f"<b>{escape(topic['title'])}</b>"]
    details = []
    if topic["supervisor"]:
        details.append(escape(topic["supervisor"]))
    if topic["area"]:
        details.append(escape(topic["area"]))
    if topic["year"]:
        details.append(str(topic["year"]))
    if details:
        lines.append(" · ".join(details))
    lines.append(fyp_status(topic["status"]))
    if topic["description"]:
        lines.append("")
        lines.append(escape(topic["description"]))
    return "\n".join(lines)


def fyp_supervisors_prompt(total: int) -> str:
    if total == 0:
        return "No supervisors recorded yet."
    return f"<b>Supervisors</b>\n{total} on file."


def fyp_areas_prompt(total: int) -> str:
    if total == 0:
        return "No areas recorded yet."
    return f"<b>Areas</b>\n{total} on file."


def fyp_years_prompt(total: int) -> str:
    if total == 0:
        return "No years recorded yet."
    return f"<b>Years</b>\n{total} on file."


def fyp_usage() -> str:
    return "Send /fyp to browse topics, or /fyp optics to search titles."


def fyp_added(identifier: int) -> str:
    return f"Topic {identifier} added."


def fyp_status_changed(status: str) -> str:
    return f"Topic marked {fyp_status(status).lower()}."


def fyp_removed(identifier: int) -> str:
    return f"Topic {identifier} removed."


def fyp_missing() -> str:
    return "That topic is gone."


def feedback_kind_prompt() -> str:
    return "<b>Send feedback</b>\nWhat is it about?"


def feedback_body_prompt(kind: str) -> str:
    return f"<b>{FEEDBACK_LABELS[kind]}</b>\nSend the details. Admins read every message."


def feedback_thanks() -> str:
    return "Sent. Admins will read it."


def feedback_report_prompt(title: str) -> str:
    return f"<b>Report a file</b>\n{escape(title)}\nSay what is wrong with it."


def feedback_too_short() -> str:
    return "Write a little more so admins can act on it."


def muted_notice() -> str:
    return "You are muted for now. You can read the library, but not post or send feedback."


def inbox_header(new_count: int, total: int, page: int, pages: int) -> str:
    if total == 0:
        return "<b>Inbox</b>\nNothing waiting."
    return f"<b>Inbox</b>\n{new_count} new · {total} total · page {page} of {pages}"


def inbox_item(entry) -> str:
    lines = [f"<b>{FEEDBACK_LABELS[entry['kind']]}</b>"]
    lines.append(f"{feedback_status(entry['status'])} · {entry['created_at'].strftime('%d %b %Y')}")
    if entry["course_code"]:
        lines.append(escape(entry["course_code"]))
    lines.append("")
    lines.append(escape(entry["body"]))
    return "\n".join(lines)


def inbox_button(entry, number: int) -> str:
    body = " ".join(entry["body"].split())[:24]
    return f"{number}. {feedback_status(entry['status'])} · {body}"


def feedback_status_changed(status: str) -> str:
    return f"Marked {feedback_status(status).lower()}."


def file_removed(title: str) -> str:
    return f"Removed “{escape(title)}” and its stored copy."


def events_header(active: bool, total: int) -> str:
    if total == 0:
        return "<b>Events</b>\nNo links right now." if active else "<b>Inactive links</b>\nNothing switched off."
    return "<b>Events</b>\nMerch and ticket links." if active else "<b>Inactive links</b>\nTap a link to switch it back on."


def event_line(event) -> str:
    date_text = event["event_date"].strftime("%d %b %Y") if event["event_date"] else "No date"
    parts = [f"<b>{escape(event['title'])}</b>", date_text]
    text = " · ".join(parts)
    if event["description"]:
        text = f"{text}\n{escape(event['description'])}"
    return text


def event_added(identifier: int) -> str:
    return f"Event link {identifier} added."


def event_removed(identifier: int) -> str:
    return f"Event link {identifier} switched off."


def event_restored(identifier: int) -> str:
    return f"Event link {identifier} switched on."


def event_usage() -> str:
    return "Send /addevent Title | https://link | 2026-12-05 | Description"


def alert_message(material: dict) -> str:
    lines = [f"<b>New {CATEGORY_LABELS[material['category']].lower()}</b>"]
    details = [escape(material["course_code"] or "General")]
    if material.get("year"):
        details.append(str(material["year"]))
    lines.append(" · ".join(details))
    lines.append(escape(material["title"]))
    return "\n".join(lines)


def material_removed_missing() -> str:
    return "That file is already gone."


def invalid_value(message: str) -> str:
    return message


def admin_only() -> str:
    return "Your role cannot do that."
