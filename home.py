# ============================================================================
# Copyright © 2026 Valrik Thakur (@valriks)
#
# Created & Developed by: Valrik Thakur
# Brand / Network: VTH NETWORK (@vthchannel)
#
# This source code is proprietary content created by Valrik Thakur.
# Unauthorized removal, modification, replacement, or concealment of the
# original author/brand credits is strictly prohibited.
#
# Redistribution, resale, rebranding, or claiming this work as your own
# without explicit permission from the author is prohibited.
#
# Any authorized use or modification must retain this copyright notice
# and the original author/brand credits.
#
# Created by Valrik Thakur | @valriks
# Powered by VTH NETWORK | @vthchannel
# ============================================================================



from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from config import BOT_TITLE
from db import users, orders
from utils import B, KB, esc, fmt_curr, edit, SEP

router = Router()


async def home_view(uid, full_name):
    u = await users.find_one({"_id": uid}) or {}
    mention = f"<a href='tg://user?id={uid}'>{esc(full_name)}</a>"
    text = (
        f"🤖 <b>{esc(BOT_TITLE)}</b>\n"
        f"<blockquote>🤩 <b>Welcome:</b> {mention} to the Best Multi Service Panel Bot</blockquote>\n"
        f"<blockquote>👤 <b><i>Select a service below to get started.</i></b></blockquote>\n"
        f"{SEP}\n"
        f"💸 <b>Your Balance:</b> {fmt_curr(u.get('balance', 0))}\n"
    )
    kb = KB(
        [B("Buy telegram Account", "buy")],
        [B("Buy WhatsApp Account", "wp_terms")],
        [B("All apps otp (VTH panel)", "s3_user_root")],
        [B("Social media services", "feature_smm_external")],
        [B("Recharge", "recharge"), B("My Profile", "stats")],
    )
    return text, kb


@router.message(Command("start"))
async def start(msg: Message, state: FSMContext):
    await state.clear()
    text, kb = await home_view(msg.from_user.id, msg.from_user.full_name)
    await msg.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "back_main")
async def back_main(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    text, kb = await home_view(cq.from_user.id, cq.from_user.full_name)
    await edit(cq, text, kb)
    await cq.answer()


@router.callback_query(F.data == "stats")
async def profile(cq: CallbackQuery):
    u = await users.find_one({"_id": cq.from_user.id}) or {}
    uname = f"@{esc(cq.from_user.username)}" if cq.from_user.username else "N/A"
    text = (
        "<b>◍ your profile</b>\n"
        f"{SEP}\n"
        f"<blockquote><b>💳 Name:</b> {esc(cq.from_user.full_name or 'User')}</blockquote>\n"
        f"<blockquote><b>🔗 Username:</b> {uname}</blockquote>\n"
        f"<blockquote><b>🆔 User ID:</b> <code>{cq.from_user.id}</code></blockquote>\n"
        f"<blockquote><b>💰 Balance:</b> {fmt_curr(u.get('balance', 0))}</blockquote>\n"
    )
    await edit(cq, text, KB([B("History", "history")], [B("Back", "back_main")]))
    await cq.answer()


@router.callback_query(F.data == "history")
async def history(cq: CallbackQuery):
    rows = await orders.find({"user_id": cq.from_user.id}).sort("date", -1).limit(15).to_list(15)
    if not rows:
        return await cq.answer("❌ No orders found yet.", show_alert=True)
    icon = {"tg": "✈️", "wa": "💬", "otp": "📲", "smm": "🌍"}
    lines = []
    for o in rows:
        d = o.get("date")
        extra = f" · <code>{esc(o['number'])}</code>" if o.get("number") else ""
        lines.append(f"{icon.get(o.get('type'), '🧾')} <b>{esc(o.get('title', 'Order'))}</b>{extra}\n"
                     f"     {fmt_curr(o.get('price', 0))} · {d.strftime('%d %b %H:%M') if d else ''}")
    await edit(cq, f"📜 <b>Your last {len(rows)} orders</b>\n{SEP}\n" + "\n".join(lines),
               KB([B("Back", "stats")]))
    await cq.answer()
