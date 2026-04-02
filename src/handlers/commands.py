import asyncio
import logging
from aiogram import Router, Bot
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram import F

from src.db import links as db
from src.services.tagger import suggest_tag, retag_all
from src import state

router = Router()
logger = logging.getLogger(__name__)

STATUS_EMOJI = {"pinned": "📌", "unread": "1️⃣", "later": "🔜", "done": "✅"}
PLATFORM_EMOJI = {"youtube": "▶️", "instagram": "📸", "tiktok": "🎵", "twitter": "🐦",
                  "reddit": "🔴", "linkedin": "💼", "github": "💻", "article": "📄"}


def _fmt_link(link: dict, idx: int | None = None, show_tag: bool = True) -> str:
    e = PLATFORM_EMOJI.get(link.get("platform", ""), "🔗")
    title = link.get("title", "").strip()
    num = f"{idx}. " if idx is not None else ""
    if not title:
        title_line = f"  <i>no title — /title {link['id']} to set</i>"
    else:
        if len(title) > 60:
            title = title[:57] + "..."
        title_line = f"  {title}"
    tag_part = f"🏷 {link['tag']} · " if show_tag else ""
    return f"{num}{e} <b>#{link['id']}</b>\n{title_line}\n  {tag_part}<a href='{link['url']}'>open</a>"


def _group_by_root(links: list[dict]) -> dict[str, dict[str, list[dict]]]:
    """Group links by root tag, then by full tag. Both levels sorted alphabetically."""
    roots: dict[str, dict[str, list[dict]]] = {}
    for link in links:
        root = link['tag'].split('/')[0]
        roots.setdefault(root, {}).setdefault(link['tag'], []).append(link)
    return roots


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 <b>Link Vault</b>\n\n"
        "Send any URL to save it. I'll fetch the title and suggest a tag.\n\n"
        "<b>Quick commands:</b>\n"
        "/list — all your saved links\n"
        "/review — weekend review mode\n"
        "/tags — your tag tree\n"
        "/help — full command list",
        parse_mode="HTML"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "<b>Link Vault — Commands</b>\n\n"
        "<b>Saving</b>\n"
        "• Send any URL → save with AI tag\n\n"
        "<b>Browsing</b>\n"
        "/list — all unread links\n"
        "/list &lt;tag&gt; — filter by tag (includes subtags)\n"
        "/review — weekend view, grouped by topic\n"
        "/find &lt;keyword&gt; — search titles & descriptions\n"
        "/archive — done links\n"
        "/archive &lt;tag&gt; — filter archive\n\n"
        "<b>Tags</b>\n"
        "/tag &lt;id&gt; &lt;tag&gt; — set/change tag\n"
        "/retag &lt;id&gt; — AI re-suggest for one link\n"
        "/retag all — AI re-tag everything\n"
        "/tags — full tag tree with counts\n\n"
        "<b>Status</b>\n"
        "/done &lt;id&gt; — archive (finished)\n"
        "/later &lt;id&gt; — snooze to end of list\n"
        "/pin &lt;id&gt; — move to top\n"
        "/unpin &lt;id&gt; — back to unread\n\n"
        "<b>Duplicates</b>\n"
        "/duplicates — scan and show all duplicate groups",
        parse_mode="HTML"
    )


@router.message(Command("list"))
async def cmd_list(message: Message, command: CommandObject):
    tag_filter = command.args.strip().lower() if command.args else None
    links = await db.list_links(tag_prefix=tag_filter)

    if not links:
        label = f"under <code>{tag_filter}</code>" if tag_filter else "saved"
        await message.answer(f"No unread links {label}.", parse_mode="HTML")
        return

    parts = [f"📚 <b>{len(links)} link(s)</b>{' under ' + tag_filter if tag_filter else ''}\n"]
    idx = 1
    roots = _group_by_root(links)
    for root in sorted(roots.keys()):
        sub_map = roots[root]
        total = sum(len(v) for v in sub_map.values())
        parts.append(f"\n━━━ <code>{root}</code> ({total}) ━━━")
        for subtag in sorted(sub_map.keys()):
            items = sub_map[subtag]
            relative = subtag[len(root) + 1:] if len(subtag) > len(root) else ""
            if relative:
                parts.append(f"  ─ <code>{relative}</code> ({len(items)})")
            for link in items:
                parts.append(_fmt_link(link, idx=idx, show_tag=False))
                idx += 1

    await message.answer("\n".join(parts), parse_mode="HTML", disable_web_page_preview=True)


@router.message(Command("review"))
async def cmd_review(message: Message):
    links = await db.list_links()
    if not links:
        await message.answer("No links to review. Go save some! 🎉")
        return

    parts = [f"📚 <b>Review — {len(links)} links</b>\n"]
    idx = 1
    roots = _group_by_root(links)
    for root in sorted(roots.keys()):
        sub_map = roots[root]
        total = sum(len(v) for v in sub_map.values())
        parts.append(f"\n━━━ <code>{root}</code> ({total}) ━━━")
        for subtag in sorted(sub_map.keys()):
            items = sub_map[subtag]
            relative = subtag[len(root) + 1:] if len(subtag) > len(root) else ""
            if relative:
                parts.append(f"  ─ <code>{relative}</code> ({len(items)})")
            for link in items:
                s = STATUS_EMOJI.get(link["status"], "•")
                title = (link.get("title") or "").strip()
                title_line = f"  {title[:60]}" if title else f"  <i>no title</i>"
                parts.append(f"{idx}. {s} <b>#{link['id']}</b>\n{title_line}\n  <a href='{link['url']}'>open</a>")
                idx += 1

    await message.answer("\n".join(parts), parse_mode="HTML", disable_web_page_preview=True)


@router.message(Command("find"))
async def cmd_find(message: Message, command: CommandObject):
    if not command.args:
        await message.answer("Usage: /find &lt;keyword&gt;", parse_mode="HTML")
        return
    links = await db.search_links(command.args.strip())
    if not links:
        await message.answer("No results found.")
        return
    parts = [f"🔍 <b>{len(links)} result(s) for '{command.args}'</b>\n"]
    for idx, link in enumerate(links, 1):
        parts.append(_fmt_link(link, idx=idx))
    await message.answer("\n".join(parts), parse_mode="HTML", disable_web_page_preview=True)


@router.message(Command("tags"))
async def cmd_tags(message: Message):
    rows = await db.get_all_tags()
    if not rows:
        await message.answer("No tags yet.")
        return
    lines = ["🏷 <b>Your Tags</b>\n"]
    for tag, count in rows:
        depth = tag.count("/")
        indent = "  " * depth
        lines.append(f"{indent}<code>{tag}</code> ({count})")
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("done"))
async def cmd_done(message: Message, command: CommandObject):
    if not command.args or not command.args.strip().isdigit():
        await message.answer("Usage: /done &lt;id&gt;", parse_mode="HTML")
        return
    link_id = int(command.args.strip())
    link = await db.get_by_id(link_id)
    if not link:
        await message.answer(f"Link #{link_id} not found.")
        return
    await db.set_status(link_id, "done")
    await message.answer(f"✅ #{link_id} archived.")


@router.message(Command("later"))
async def cmd_later(message: Message, command: CommandObject):
    if not command.args or not command.args.strip().isdigit():
        await message.answer("Usage: /later &lt;id&gt;", parse_mode="HTML")
        return
    link_id = int(command.args.strip())
    await db.set_status(link_id, "later")
    await message.answer(f"🔜 #{link_id} moved to later.")


@router.message(Command("pin"))
async def cmd_pin(message: Message, command: CommandObject):
    if not command.args or not command.args.strip().isdigit():
        await message.answer("Usage: /pin &lt;id&gt;", parse_mode="HTML")
        return
    link_id = int(command.args.strip())
    await db.set_status(link_id, "pinned")
    await message.answer(f"📌 #{link_id} pinned.")


@router.message(Command("unpin"))
async def cmd_unpin(message: Message, command: CommandObject):
    if not command.args or not command.args.strip().isdigit():
        await message.answer("Usage: /unpin &lt;id&gt;", parse_mode="HTML")
        return
    link_id = int(command.args.strip())
    await db.set_status(link_id, "unread")
    await message.answer(f"✅ #{link_id} unpinned.")


@router.message(Command("tag"))
async def cmd_tag(message: Message, command: CommandObject):
    if not command.args:
        await message.answer("Usage: /tag &lt;id&gt; &lt;tag&gt;", parse_mode="HTML")
        return
    parts = command.args.strip().split(maxsplit=1)
    if len(parts) != 2 or not parts[0].isdigit():
        await message.answer("Usage: /tag &lt;id&gt; &lt;tag&gt;\nExample: /tag 42 dev/react", parse_mode="HTML")
        return
    link_id, new_tag = int(parts[0]), parts[1].lower().strip("/")
    link = await db.get_by_id(link_id)
    if not link:
        await message.answer(f"Link #{link_id} not found.")
        return
    await db.set_tag(link_id, new_tag)
    await message.answer(f"🏷 #{link_id} tag updated to <code>{new_tag}</code>", parse_mode="HTML")


@router.message(Command("retag"))
async def cmd_retag(message: Message, command: CommandObject):
    arg = (command.args or "").strip().lower()

    if arg == "all":
        msg = await message.answer("⏳ Re-tagging all links with AI...")
        links = await db.get_all_active()
        tag_rows = await db.get_all_tags()
        existing_tags = [t[0] for t in tag_rows]
        results = await retag_all(links, existing_tags)
        changed = 0
        for link_id, new_tag in results:
            old = next((l["tag"] for l in links if l["id"] == link_id), "")
            if old != new_tag:
                await db.set_tag(link_id, new_tag)
                changed += 1
        await msg.edit_text(f"✅ Re-tagged {len(results)} links, {changed} changed.")
        return

    if arg.isdigit():
        link_id = int(arg)
        link = await db.get_by_id(link_id)
        if not link:
            await message.answer(f"Link #{link_id} not found.")
            return
        tag_rows = await db.get_all_tags()
        existing_tags = [t[0] for t in tag_rows]
        new_tag = await suggest_tag(link["title"], link["description"], link["platform"], existing_tags)
        await db.set_tag(link_id, new_tag)
        await message.answer(f"🏷 #{link_id} re-tagged to <code>{new_tag}</code>", parse_mode="HTML")
        return

    await message.answer("Usage:\n/retag &lt;id&gt; — retag one link\n/retag all — retag everything", parse_mode="HTML")


@router.message(Command("archive"))
async def cmd_archive(message: Message, command: CommandObject):
    tag_filter = command.args.strip().lower() if command.args else None
    links = await db.list_archive(tag_prefix=tag_filter)
    if not links:
        label = f"under <code>{tag_filter}</code>" if tag_filter else ""
        await message.answer(f"No archived links {label}.", parse_mode="HTML")
        return
    parts = [f"🗄 <b>Archive — {len(links)} link(s)</b>\n"]
    for idx, link in enumerate(links, 1):
        parts.append(_fmt_link(link, idx=idx))
    await message.answer("\n".join(parts), parse_mode="HTML", disable_web_page_preview=True)


@router.message(Command("duplicates"))
async def cmd_duplicates(message: Message):
    from src.services.duplicates import group_all_duplicates
    msg = await message.answer("⏳ Scanning for duplicates...")
    all_links = await db.get_all_active()
    groups = group_all_duplicates(all_links)

    if not groups:
        await msg.edit_text("✅ No duplicates found!")
        return

    await msg.edit_text(f"Found <b>{len(groups)} duplicate group(s)</b>. Sending details...", parse_mode="HTML")

    for i, group in enumerate(groups, 1):
        lines = [f"━━━ Group {i} ━━━\n"]
        for link in group:
            title = (link.get("title") or link["url"])[:50]
            lines.append(f"<b>#{link['id']}</b> {title}\n🏷 {link['tag']}\n🔗 {link['url']}\n")

        buttons = []
        for link in group:
            buttons.append([InlineKeyboardButton(
                text=f"Keep #{link['id']} ({link['tag']})",
                callback_data=f"dup_keep:{link['id']}:{','.join(str(l['id']) for l in group if l['id'] != link['id'])}"
            )])
        buttons.append([InlineKeyboardButton(text="Keep all", callback_data=f"dup_keepall:{i}")])

        await message.answer(
            "\n".join(lines),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            disable_web_page_preview=True
        )


@router.callback_query(F.data.startswith("dup_keep:"))
async def cb_dup_keep(cb: CallbackQuery):
    parts = cb.data.split(":")
    keep_id = int(parts[1])
    delete_ids = [int(x) for x in parts[2].split(",") if x]
    for did in delete_ids:
        await db.delete_link(did)
    await cb.answer(f"Kept #{keep_id}, deleted {len(delete_ids)} duplicate(s).")
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer(f"✅ Kept <b>#{keep_id}</b>, removed {len(delete_ids)} duplicate(s).", parse_mode="HTML")


@router.callback_query(F.data.startswith("dup_keepall:"))
async def cb_dup_keepall(cb: CallbackQuery):
    await cb.answer("Keeping all.")
    await cb.message.edit_reply_markup(reply_markup=None)


# ── Reminder ──────────────────────────────────────────────────────────────────

def _reminder_keyboard(link_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Done", callback_data=f"rem_done:{link_id}"),
            InlineKeyboardButton(text="⏰ +15 min", callback_data=f"rem_snooze:{link_id}:15"),
            InlineKeyboardButton(text="⏰ +30 min", callback_data=f"rem_snooze:{link_id}:30"),
        ],
        [
            InlineKeyboardButton(text="🔜 Save for later", callback_data=f"rem_later:{link_id}"),
        ]
    ])


async def _send_reminder(bot: Bot, chat_id: int, link_id: int):
    link = await db.get_by_id(link_id)
    if not link or link["status"] == "done":
        return
    title = (link.get("title") or link["url"])[:60]
    await bot.send_message(
        chat_id,
        f"⏰ <b>Still reading?</b>\n\n"
        f"<b>#{link_id}</b> — {title}\n"
        f"🏷 {link['tag']}",
        parse_mode="HTML",
        reply_markup=_reminder_keyboard(link_id)
    )


@router.message(Command("reading"))
async def cmd_reading(message: Message, command: CommandObject):
    args = (command.args or "").strip().split()
    if not args or not args[0].isdigit():
        await message.answer(
            "Usage:\n"
            "/reading &lt;id&gt; — remind in 20 min (default)\n"
            "/reading &lt;id&gt; &lt;minutes&gt; — custom time\n\n"
            "Example: /reading 42 15",
            parse_mode="HTML"
        )
        return

    link_id = int(args[0])
    minutes = int(args[1]) if len(args) > 1 and args[1].isdigit() else 20

    link = await db.get_by_id(link_id)
    if not link:
        await message.answer(f"Link #{link_id} not found.")
        return

    # Cancel existing reminder for this link if any
    existing = state.reminders.get(link_id)
    if existing and not existing.done():
        existing.cancel()

    chat_id = message.chat.id
    bot = message.bot

    async def _task():
        # Initial wait
        await asyncio.sleep(minutes * 60)
        # Keep sending every 5 min until user replies (task is cancelled)
        while True:
            link = await db.get_by_id(link_id)
            if not link or link["status"] == "done":
                break
            await _send_reminder(bot, chat_id, link_id)
            await asyncio.sleep(5 * 60)
        state.reminders.pop(link_id, None)

    state.reminders[link_id] = asyncio.create_task(_task())
    title = (link.get("title") or link["url"])[:50]
    await message.answer(
        f"⏱ Reminder set for <b>#{link_id}</b> — {title}\n"
        f"I'll check in after <b>{minutes} min</b>, then every 5 min until you reply.",
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("rem_done:"))
async def cb_rem_done(cb: CallbackQuery):
    link_id = int(cb.data.split(":")[1])
    await db.set_status(link_id, "done")
    state.reminders.pop(link_id, None)
    await cb.answer("Marked as done!")
    await cb.message.edit_text(
        cb.message.text + "\n\n✅ <i>Marked as done.</i>",
        parse_mode="HTML", reply_markup=None
    )


@router.callback_query(F.data.startswith("rem_snooze:"))
async def cb_rem_snooze(cb: CallbackQuery):
    parts = cb.data.split(":")
    link_id, minutes = int(parts[1]), int(parts[2])

    existing = state.reminders.get(link_id)
    if existing and not existing.done():
        existing.cancel()

    chat_id = cb.message.chat.id
    bot = cb.bot

    async def _task():
        await asyncio.sleep(minutes * 60)
        while True:
            link = await db.get_by_id(link_id)
            if not link or link["status"] == "done":
                break
            await _send_reminder(bot, chat_id, link_id)
            await asyncio.sleep(5 * 60)
        state.reminders.pop(link_id, None)

    state.reminders[link_id] = asyncio.create_task(_task())
    await cb.answer(f"Snoozed {minutes} min!")
    await cb.message.edit_reply_markup(reply_markup=None)


@router.callback_query(F.data.startswith("rem_later:"))
async def cb_rem_later(cb: CallbackQuery):
    link_id = int(cb.data.split(":")[1])
    await db.set_status(link_id, "later")
    state.reminders.pop(link_id, None)
    await cb.answer("Moved to later.")
    await cb.message.edit_text(
        cb.message.text + "\n\n🔜 <i>Saved for later.</i>",
        parse_mode="HTML", reply_markup=None
    )


# ── Title editing ─────────────────────────────────────────────────────────────

@router.message(Command("del"))
async def cmd_del(message: Message, command: CommandObject):
    if not command.args or not command.args.strip().isdigit():
        await message.answer("Usage: /del &lt;id&gt;\nExample: /del 5", parse_mode="HTML")
        return
    link_id = int(command.args.strip())
    link = await db.get_by_id(link_id)
    if not link:
        await message.answer(f"Link #{link_id} not found.")
        return
    await db.delete_link(link_id)
    title = link.get("title") or link["url"]
    await message.answer(f"🗑 Deleted <b>#{link_id}</b>: {title}", parse_mode="HTML")


@router.message(Command("title"))
async def cmd_title(message: Message, command: CommandObject):
    if not command.args:
        await message.answer("Usage: /title &lt;id&gt; &lt;new title&gt;\nExample: /title 1 تعلم ريأكت هوكس", parse_mode="HTML")
        return
    parts = command.args.strip().split(maxsplit=1)
    if len(parts) < 2 or not parts[0].isdigit():
        await message.answer("Usage: /title &lt;id&gt; &lt;new title&gt;", parse_mode="HTML")
        return
    link_id, new_title = int(parts[0]), parts[1].strip()
    link = await db.get_by_id(link_id)
    if not link:
        await message.answer(f"Link #{link_id} not found.")
        return
    await db.set_title(link_id, new_title)
    await message.answer(f"📝 Title updated for <b>#{link_id}</b>:\n{new_title}", parse_mode="HTML")


@router.callback_query(F.data.startswith("title_edit:"))
async def cb_title_edit(cb: CallbackQuery):
    link_id = int(cb.data.split(":")[1])
    state.pending_titles[cb.from_user.id] = link_id
    await cb.answer()
    await cb.message.answer(
        f"Send the new title for <b>#{link_id}</b>\nYou can write in Arabic or English.",
        parse_mode="HTML"
    )
    await cb.message.edit_reply_markup(reply_markup=None)
