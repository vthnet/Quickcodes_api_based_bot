import time
from html import escape
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery,
                           CopyTextButton, LinkPreviewOptions)
from aiogram.exceptions import TelegramBadRequest

SEP = "––––––—–————––––——–––•"
NOPREV = LinkPreviewOptions(is_disabled=True)


def esc(t):
    return escape(str(t if t is not None else ""))


def fmt_curr(v):
    return f"₹{float(v or 0):.2f}"


def fmt_short(v):
    return f"₹{float(v or 0):g}"


def short(t, n):
    t = str(t)
    return t if len(t) <= n else t[:n - 1] + "…"


def B(text, cb=None, url=None, copy=None):
    if url:
        return InlineKeyboardButton(text=text, url=url)
    if copy is not None:
        return InlineKeyboardButton(text=text, copy_text=CopyTextButton(text=str(copy)))
    return InlineKeyboardButton(text=text, callback_data=cb)


def KB(*rows):
    return InlineKeyboardMarkup(inline_keyboard=[list(r) for r in rows if r])


def chunk(items, n):
    return [items[i:i + n] for i in range(0, len(items), n)]


def pager_row(page, pages, cb_fn, noop):
    if pages <= 1:
        return []
    row = []
    if page > 0:
        row.append(B("⬅️ Prev", cb_fn(page - 1)))
    row.append(B(f"{page + 1}/{pages}", noop))
    if page < pages - 1:
        row.append(B("Next ➡️", cb_fn(page + 1)))
    return row


async def edit(target, text, markup=None):
    """Edit the screen. If that is impossible (photo message, etc.) replace it."""
    msg = target.message if isinstance(target, CallbackQuery) else target
    try:
        return await msg.edit_text(text, reply_markup=markup, parse_mode="HTML", link_preview_options=NOPREV)
    except TelegramBadRequest as e:
        if "not modified" in str(e).lower():
            return msg
    except Exception:
        pass
    try:
        await msg.delete()
    except Exception:
        pass
    return await msg.answer(text, reply_markup=markup, parse_mode="HTML", link_preview_options=NOPREV)


_last = {}


def is_spamming(uid, key="x", cooldown=3.0):
    now = time.time()
    k = (uid, key)
    if now - _last.get(k, 0) < cooldown:
        return True
    _last[k] = now
    return False


def normalize_support(link):
    link = (link or "").strip()
    if not link:
        return ""
    if link.startswith("@"):
        return f"https://t.me/{link[1:]}"
    if link.startswith(("t.me/", "telegram.me/")):
        return "https://" + link
    if link.startswith(("http://", "https://", "tg://")):
        return link
    return f"https://t.me/{link}"
