import logging
from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram import F

from src.db import links as db
from src.services.tagger import suggest_tag, retag_all

router = Router()
logger = logging.getLogger(__name__)

STATUS_EMOJI = {"pinned": "📌", "unread": "1️⃣", "later": "🔜", "done": "✅"}
PLATFORM_EMOJI = {"youtube": "▶️", "instagram": "📸", "tiktok": "🎵", "twitter": "🐦",
                  "reddit": "🔴", "linkedin": "💼", "github": "💻", "article": "📄"}


def _fmt_link(link: dict) -> str:
    e = PLATFORM_EMOJI.get(link.get("platform", ""), "🔗")
    title = link.get("title") or link["url"]
    if len(title) > 60:
        title = title[:57] + "..."
    return f"{e} <b>#{link['id']}</b> {title}\n    🏷 {link['tag']} · <a href='{link['url']}'>open</a>"


def _group_by_tag(links: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for link in links:
        groups.setdefault(link["tag"], []).append(link)
    return groups


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

    groups = _group_by_tag(links)
    parts = [f"📚 <b>{len(links)} link(s)</b>{' under ' + tag_filter if tag_filter else ''}\n"]
    for tag, items in groups.items():
        parts.append(f"\n━━━ <code>{tag}</code> ({len(items)}) ━━━")
        for link in items:
            parts.append(_fmt_link(link))

    await message.answer("\n".join(parts), parse_mode="HTML", disable_web_page_preview=True)


@router.message(Command("review"))
async def cmd_review(message: Message):
    links = await db.list_links()
    if not links:
        await message.answer("No links to review. Go save some! 🎉")
        return

    groups = _group_by_tag(links)
    parts = [f"📚 <b>Review — {len(links)} links</b>\n"]
    for tag, items in sorted(groups.items()):
        parts.append(f"\n━━━ <code>{tag}</code> ({len(items)}) ━━━")
        for link in items:
            e = STATUS_EMOJI.get(link["status"], "•")
            title = (link.get("title") or link["url"])[:55]
            parts.append(f"{e} <b>#{link['id']}</b> <a href='{link['url']}'>{title}</a>")

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
    for link in links:
        parts.append(_fmt_link(link))
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
    for link in links:
        parts.append(_fmt_link(link))
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
