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


"""Buy Telegram account  ->  runs on the Quick Codes Server 2 API."""
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from db import service_on, get_balance
from flows import s2_view, buy_tg, tg_code
from flags import flag_for, strip_flags
from utils import B, KB, esc, fmt_curr, fmt_short, edit, is_spamming, chunk

router = Router()
TITLE = "🚀 Telegram Accounts"
PER_PAGE, PER_ROW = 24, 2
LINE = "━━━━━━━━━━━━━━━━━━━━━"


class TGState(StatesGroup):
    waiting_search = State()


async def build_menu(page=0, query=None):
    rows = await s2_view()
    if rows is None:
        return ("❌ <b>Service is temporarily unavailable.</b>\n<i>Please try again later.</i>",
                KB([B("Home", "back_main")]))
    if not rows:
        return "❌ <b>No countries available right now.</b>", KB([B("Home", "back_main")])
    if query:
        q = query.lower().strip()
        rows = [r for r in rows if q in r["country_code"].lower() or q in r["name"].lower()
                or q in flag_for(strip_flags(r["name"])) or q == r["country_code"].lower()]
        if not rows:
            return (f"❌ <b>No countries found for:</b> <code>{esc(query)}</code>",
                    KB([B("Search", "s2:search")], [B("Back", "s2:page:0")]))
    pages = (len(rows) - 1) // PER_PAGE + 1
    page = max(0, min(page, pages - 1))
    btns = []
    for r in rows[page * PER_PAGE:(page + 1) * PER_PAGE]:
        label = f"{'❌ ' if r['stock'] <= 0 else ''}{r['name']}|{fmt_short(r['my_price'])}"
        btns.append(B(label[:64], f"s2:country:{r['country_code']}"))
    kb_rows = chunk(btns, PER_ROW)
    if pages > 1 and not query:
        nums = [B(f"[{p + 1}]" if p == page else str(p + 1), f"s2:page:{p}") for p in range(pages)]
        kb_rows += chunk(nums, 8)
    kb_rows.append([B("Search", "s2:search")])
    kb_rows.append([B("Home", "back_main")])
    head = (f"<b>🔍 Search Results for:</b> <code>{esc(query)}</code>" if query else f"<b>{TITLE}</b>")
    text = (f"{head}\n{LINE}\n<b>📄 Page:</b> {page + 1}/{pages}\n{LINE}\n"
            f"<i>Select a country to purchase:</i>")
    return text, KB(*kb_rows)


async def show_menu(target, uid, page=0, query=None):
    text, kb = await build_menu(page, query)
    if not text.startswith("❌"):
        text = f"💰 <b>Your Balance:</b> {fmt_curr(await get_balance(uid))}\n{text}"
    await edit(target, text, kb)


async def gate(cq):
    if not await service_on("tg"):
        await cq.answer("⚠️ Telegram accounts are under maintenance. Please try again later!", show_alert=True)
        return False
    return True


@router.callback_query(F.data == "buy")
async def entry(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await gate(cq):
        return
    await cq.answer()
    await show_menu(cq, cq.from_user.id, 0)


@router.callback_query(F.data.startswith("s2:page:"))
async def paginate(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await gate(cq):
        return
    await cq.answer()
    await show_menu(cq, cq.from_user.id, int(cq.data.split(":")[2]))


@router.callback_query(F.data == "s2:search")
async def search_prompt(cq: CallbackQuery, state: FSMContext):
    await cq.answer("🔍 Enter search query...")
    await edit(cq, f"<b>🔍 Search Countries</b>\n{LINE}\n"
                   "<i>Send country code (e.g. <code>US</code>, <code>IN</code>) or country name/flag.</i>\n"
                   "<i>Example: <code>🇮🇳</code> or <code>India</code> or <code>IN</code></i>",
               KB([B("Back", "s2:page:0")]))
    await state.set_state(TGState.waiting_search)


@router.message(StateFilter(TGState.waiting_search), F.text, ~F.text.startswith("/"))
async def search_result(msg: Message, state: FSMContext):
    await state.clear()
    q = msg.text.strip()
    wait = await msg.answer("🔍 <i>Searching…</i>", parse_mode="HTML")
    await show_menu(wait, msg.from_user.id, 0, query=q)


@router.callback_query(F.data.startswith("s2:country:"))
async def country(cq: CallbackQuery):
    if not await gate(cq):
        return
    code = cq.data.split(":", 2)[2]
    await cq.answer("🔄 Fetching details...")
    rows = await s2_view()
    row = next((r for r in rows or [] if r["country_code"] == code), None)
    if not row:
        return await cq.answer("❌ Country no longer available", show_alert=True)
    bal = await get_balance(cq.from_user.id)
    price, qty = row["my_price"], int(row["stock"])
    text = (f"<b>{TITLE} — Purchase</b>\n{LINE}\n"
            f"<blockquote><b>🌍 Country:</b> {esc(row['name'])}\n"
            f"<b>📊 Stock:</b> {qty} accounts\n"
            f"<b>🏷️ Price:</b> {fmt_short(price)}</blockquote>\n{LINE}\n"
            f"💰 <b>Your Balance:</b> {fmt_curr(bal)}\n")
    if bal < price:
        text += f"\n❌ <b>Insufficient Balance!</b>\n<i>Shortage: {fmt_curr(price - bal)}</i>"
        kb = KB([B("Recharge •", "recharge")], [B("Back •", "s2:page:0")], [B("Home •", "back_main")])
    elif qty < 1:
        text += "\n⚠️ <b>Out of Stock!</b>"
        kb = KB([B("Back •", "s2:page:0")], [B("Home •", "back_main")])
    else:
        text += "\n✅ <b>Ready to purchase?</b>"
        kb = KB([B(f"🛒 Buy for {fmt_short(price)}", f"s2:confirm:{code}:{price:.2f}")],
                [B("Back", "s2:page:0")], [B("Home", "back_main")])
    await edit(cq, text, kb)


@router.callback_query(F.data.startswith("s2:confirm:"))
async def confirm(cq: CallbackQuery):
    if not await gate(cq):
        return
    if is_spamming(cq.from_user.id, "s2buy", 5):
        return await cq.answer("⏳ Purchase processing... Please wait 5s", show_alert=True)
    _, _, code, shown = cq.data.split(":")
    await cq.answer("🔄 Processing purchase...")
    await edit(cq, "<b>🔄 Processing Purchase...</b>\n<i>Contacting servers...</i>")
    r = await buy_tg(cq.from_user.id, code, float(shown))
    back = KB([B("◾ Back", "s2:page:0")], [B("◾ Home", "back_main")])
    k = r["kind"]
    if k == "ok":
        o = r["order"]
        text = (f"<pre>✅ Purchased Successfully!</pre>\n{LINE}\n"
                f"<b>🌍 Country:</b> {esc(r['country'])}\n"
                f"<b>📞 Number:</b> <code>{esc(o['number'])}</code>\n"
                f"<b>🏷️ Price:</b> {fmt_short(o['price'])}\n"
                f"<b>💸 Balance:</b> {fmt_curr(r['balance'])}\n{LINE}\n"
                f"<i>Click 'Get OTP' to receive the login code.</i>")
        return await edit(cq, text, KB([B("📩 Get OTP", f"s2:otp:{o['api_order_id']}"),
                                         B("📋 Copy Number", copy=o["number"])]))
    if k == "price":
        await cq.message.answer(f"ℹ️ Price changed to <b>{fmt_short(r['price'])}</b>. Please confirm again.", parse_mode="HTML")
        return await show_menu(cq, cq.from_user.id, 0)
    if k == "funds":
        return await edit(cq, f"❌ <b>Insufficient Balance!</b>\n<i>Shortage: {fmt_curr(r['need'])}</i>",
                          KB([B("Recharge •", "recharge")], [B("Back •", "s2:page:0")]))
    await edit(cq, f"❌ <b>Purchase Failed</b>\n{r['text']}", back)


@router.callback_query(F.data.startswith("s2:otp:"))
async def get_otp(cq: CallbackQuery):
    if is_spamming(cq.from_user.id, "s2otp", 3):
        return await cq.answer("⏳ OTP fetch in progress...", show_alert=True)
    oid = cq.data.split(":", 2)[2]
    r = await tg_code(cq.from_user.id, oid)
    if r["kind"] == "wait":
        return await cq.answer("⏳ No code received yet. Try again in a few seconds...", show_alert=True)
    if r["kind"] == "missing":
        return await cq.answer("❌ Order not found.", show_alert=True)
    if r["kind"] != "ok":
        return await cq.answer("⚠️ Server busy. Please try again in a moment.", show_alert=True)
    await cq.answer()
    code, pw = r["code"], r.get("password") or "None"
    await cq.message.answer(
        f"<pre>Order Completed ✅</pre>\n✅ <b>𝐍𝗨𝐌𝐁𝐄𝐑</b> - <code>{esc(r['number'])}</code>\n"
        f"💬 <b>𝐂𝐎𝐃𝐄</b> - <code>{esc(code)}</code>\n💬 <b>𝐏𝐀𝐒𝐒</b> - <code>{esc(pw)}</code>\n"
        f"<i>🚀 Server - 2 </i>", parse_mode="HTML",
        reply_markup=KB([B("Copy OTP•", copy=code), B("Copy Pass•", copy=pw)]))
