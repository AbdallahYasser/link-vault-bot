import re
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from src.db import links as db
from src.services.tagger import suggest_tag
from src.utils.url_normalizer import normalize
from src.utils.platform import detect
from src import state

router = Router()
logger = logging.getLogger(__name__)

URL_RE = re.compile(r'https?://[^\s]+')


def _link_keyboard(link_id: int, suggested_tag: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Keep tag", callback_data=f"tag_ok:{link_id}"),
            InlineKeyboardButton(text="✏️ Change tag", callback_data=f"tag_edit:{link_id}"),
        ],
        [
            InlineKeyboardButton(text="📝 Edit title", callback_data=f"title_edit:{link_id}"),
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
    existing = await db.get_by_url(url, message.from_user.id)
    if existing:
        await message.answer(
            f"⛔ Already saved as <b>#{existing['user_link_id']}</b> [{existing['tag']}]\n"
            f"🔗 {existing['url']}",
            parse_mode="HTML"
        )
        return

    state.pending_new_links[message.from_user.id] = {
        "url": url,
        "original_url": original_url,
        "platform": platform,
    }
    await message.answer(
        "🔗 Got it! Send me a title for this link.\n"
        "<i>(type <code>-</code> to skip)</i>",
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("tag_ok:"))
async def cb_tag_ok(cb: CallbackQuery):
    await cb.answer("Tag confirmed!")
    await cb.message.edit_reply_markup(reply_markup=None)


@router.callback_query(F.data.startswith("tag_edit:"))
async def cb_tag_edit(cb: CallbackQuery):
    link_id = int(cb.data.split(":")[1])
    await cb.answer()

    tag_rows = await db.get_all_tags(cb.from_user.id)
    buttons = []
    row = []
    for tag, _ in tag_rows:
        row.append(InlineKeyboardButton(text=tag, callback_data=f"tag_set:{link_id}:{tag}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="✏️ Type new tag", callback_data=f"tag_type:{link_id}")])

    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await cb.message.answer(
        f"Choose a tag for <b>#{link_id}</b> or type a new one:",
        parse_mode="HTML",
        reply_markup=markup
    )
    await cb.message.edit_reply_markup(reply_markup=None)


@router.callback_query(F.data.startswith("tag_set:"))
async def cb_tag_set(cb: CallbackQuery):
    parts = cb.data.split(":", 2)
    link_id, new_tag = int(parts[1]), parts[2]
    await db.set_tag(link_id, new_tag, cb.from_user.id)
    await cb.answer("Tag updated!")
    await cb.message.edit_text(
        f"✅ Tag updated to <code>{new_tag}</code> for <b>#{link_id}</b>",
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("tag_type:"))
async def cb_tag_type(cb: CallbackQuery):
    link_id = int(cb.data.split(":")[1])
    await cb.answer()
    state.pending_tags[cb.from_user.id] = link_id
    await cb.message.answer(
        f"Send the new tag for <b>#{link_id}</b>\n"
        f"Example: <code>dev/react</code> or <code>clothes/man/winter</code>",
        parse_mode="HTML"
    )
    await cb.message.edit_reply_markup(reply_markup=None)


@router.message(F.text & ~F.text.startswith("/"))
async def handle_plain_text(message: Message):
    user_id = message.from_user.id

    if user_id in state.pending_new_links:
        data = state.pending_new_links.pop(user_id)
        title = "" if message.text.strip() == "-" else message.text.strip()

        status_msg = await message.answer("⏳ Tagging...")
        tag_rows = await db.get_all_tags(user_id)
        existing_tags = [t[0] for t in tag_rows]
        suggested = await suggest_tag(title or data["platform"], data["platform"], existing_tags)
        link_id = await db.save(data["url"], data["original_url"], title, data["platform"], suggested, user_id)

        await status_msg.edit_text(
            f"✅ Saved <b>#{link_id}</b>\n"
            f"📎 {title or '(no title)'}\n"
            f"🏷 <code>{suggested}</code>",
            parse_mode="HTML",
            reply_markup=_link_keyboard(link_id, suggested)
        )

    elif user_id in state.pending_titles:
        link_id = state.pending_titles.pop(user_id)
        new_title = message.text.strip()
        await db.set_title(link_id, new_title, user_id)
        await message.answer(f"📝 Title updated for <b>#{link_id}</b>:\n{new_title}", parse_mode="HTML")

    elif user_id in state.pending_tags:
        link_id = state.pending_tags.pop(user_id)
        new_tag = message.text.strip().lower().strip("/")
        await db.set_tag(link_id, new_tag, user_id)
        await message.answer(f"✅ Tag updated to <code>{new_tag}</code> for <b>#{link_id}</b>", parse_mode="HTML")

    else:
        await message.answer("Send a URL to save it, or use /help for commands.")
