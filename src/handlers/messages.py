import re
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from src.db import links as db
from src.services.scraper import fetch_metadata
from src.services.tagger import suggest_tag
from src.services.duplicates import find_smart_duplicates
from src.utils.url_normalizer import normalize
from src.utils.platform import detect

router = Router()
logger = logging.getLogger(__name__)

URL_RE = re.compile(r'https?://[^\s]+')


def _link_keyboard(link_id: int, suggested_tag: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Keep tag", callback_data=f"tag_ok:{link_id}"),
            InlineKeyboardButton(text="✏️ Change tag", callback_data=f"tag_edit:{link_id}"),
        ]
    ])


def _dup_keyboard(new_url: str, existing_id: int) -> InlineKeyboardMarkup:
    import urllib.parse
    enc = urllib.parse.quote(new_url, safe="")
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Skip (same thing)", callback_data=f"dup_skip:{existing_id}"),
            InlineKeyboardButton(text="➕ Save both", callback_data=f"dup_save:{enc}:{existing_id}"),
        ],
        [
            InlineKeyboardButton(text="🔀 Merge tags", callback_data=f"dup_merge:{existing_id}"),
        ]
    ])


@router.message(F.text.regexp(URL_RE))
async def handle_url(message: Message):
    match = URL_RE.search(message.text)
    if not match:
        return
    original_url = match.group(0)
    url = normalize(original_url)
    platform = detect(url)

    # Exact duplicate check
    existing = await db.get_by_url(url)
    if existing:
        await message.answer(
            f"⛔ Already saved as <b>#{existing['id']}</b> [{existing['tag']}]\n"
            f"🔗 {existing['url']}",
            parse_mode="HTML"
        )
        return

    status_msg = await message.answer("⏳ Fetching...")

    meta = await fetch_metadata(url)
    title = meta["title"] or url
    description = meta["description"]

    # Smart duplicate check
    all_links = await db.get_all_active()
    smart_dups = find_smart_duplicates(title, description, all_links)
    if smart_dups:
        dup = smart_dups[0]
        await status_msg.edit_text(
            f"⚠️ <b>Similar content already saved:</b>\n\n"
            f"<b>New:</b>\n📎 {title}\n🔗 {original_url}\n\n"
            f"<b>Existing (#{dup['id']}):</b>\n📎 {dup['title']}\n🔗 {dup['url']}\n"
            f"🏷 {dup['tag']}",
            parse_mode="HTML",
            reply_markup=_dup_keyboard(url, dup["id"])
        )
        return

    # Get existing tags for AI context
    tag_rows = await db.get_all_tags()
    existing_tags = [t[0] for t in tag_rows]

    suggested = await suggest_tag(title, description, platform, existing_tags)
    link_id = await db.save(url, original_url, title, description, platform, suggested)

    await status_msg.edit_text(
        f"✅ Saved <b>#{link_id}</b>\n"
        f"📎 {title}\n"
        f"🏷 <code>{suggested}</code>",
        parse_mode="HTML",
        reply_markup=_link_keyboard(link_id, suggested)
    )


@router.callback_query(F.data.startswith("tag_ok:"))
async def cb_tag_ok(cb: CallbackQuery):
    await cb.answer("Tag confirmed!")
    await cb.message.edit_reply_markup(reply_markup=None)


@router.callback_query(F.data.startswith("tag_edit:"))
async def cb_tag_edit(cb: CallbackQuery):
    link_id = int(cb.data.split(":")[1])
    await cb.answer()
    await cb.message.answer(
        f"Send the new tag for <b>#{link_id}</b>\n"
        f"Example: <code>dev/react</code> or <code>clothes/man/winter</code>",
        parse_mode="HTML"
    )
    # Store pending edit in bot data
    cb.bot["pending_tag"] = cb.bot.get("pending_tag", {})
    cb.bot["pending_tag"][cb.from_user.id] = link_id
    await cb.message.edit_reply_markup(reply_markup=None)


@router.callback_query(F.data.startswith("dup_skip:"))
async def cb_dup_skip(cb: CallbackQuery):
    await cb.answer("Skipped.")
    await cb.message.edit_text(cb.message.text + "\n\n<i>Skipped — not saved.</i>", parse_mode="HTML", reply_markup=None)


@router.callback_query(F.data.startswith("dup_save:"))
async def cb_dup_save(cb: CallbackQuery):
    import urllib.parse
    parts = cb.data.split(":", 2)
    url = urllib.parse.unquote(parts[1])
    await cb.answer("Saving...")
    meta = await fetch_metadata(url)
    tag_rows = await db.get_all_tags()
    existing_tags = [t[0] for t in tag_rows]
    suggested = await suggest_tag(meta["title"], meta["description"], detect(url), existing_tags)
    link_id = await db.save(url, url, meta["title"], meta["description"], detect(url), suggested)
    await cb.message.edit_text(
        f"✅ Saved as <b>#{link_id}</b> under <code>{suggested}</code>",
        parse_mode="HTML", reply_markup=None
    )


@router.callback_query(F.data.startswith("dup_merge:"))
async def cb_dup_merge(cb: CallbackQuery):
    await cb.answer("Tags merged!")
    await cb.message.edit_text(cb.message.text + "\n\n<i>Tags merged into existing entry.</i>", parse_mode="HTML", reply_markup=None)


@router.message(F.text & ~F.text.startswith("/"))
async def handle_plain_text(message: Message):
    pending = message.bot.get("pending_tag", {})
    if message.from_user.id in pending:
        link_id = pending.pop(message.from_user.id)
        new_tag = message.text.strip().lower().strip("/")
        await db.set_tag(link_id, new_tag)
        await message.answer(f"✅ Tag updated to <code>{new_tag}</code> for <b>#{link_id}</b>", parse_mode="HTML")
    else:
        await message.answer("Send a URL to save it, or use /help for commands.")
