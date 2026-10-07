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

"""All apps OTP (VTH panel) + WhatsApp accounts  ->  both run on the Quick Codes Server 3 API."""
import asyncio
import os
import time
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from db import service_on, get_balance, tasks
from flows import (s3_catalog, s3_countries, s3_offers, buy_s3, s3_poll, s3_cancel, drop_s3_cache,
                   find_service, search_services, is_wa, norm, OTP_TIMEOUT, CANCEL_LOCK)
from flags import flag_for
from notify import get_bot
from utils import B, KB, esc, fmt_curr, fmt_short, edit, is_spamming, chunk, NOPREV

router = Router()
PER_SERVICES, PER_COUNTRIES = 20, 16
LINE = "━━━━━━━━━━━━━━━━━━━━"
WP_GUIDE_URL = os.getenv("WP_GUIDE_URL", "").strip()
POPULAR = ["Instagram", "Facebook", "Google", "Twitter", "TikTok", "Discord", "Snapchat", "Amazon", "OpenAI", "Netflix"]

BUSY_TXT = ("⚠️ <b>Provider is busy right now</b>\nLive rates could not be loaded. "
            "You were not charged — please try again in a moment.")
TELEGRAM_NOTE = ("<blockquote>⚠️ <b>Use this service only for Telegram number change.</b>\n"
                 "🛒 To buy ready-made Telegram accounts use <b>Buy telegram Account</b> on the home menu.</blockquote>")
WHATSAPP_TIPS = (
    "<b>🔐 Secure Your WhatsApp Acc0unt</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    "<blockquote expandable>"
    "• after login do not use the account for atleast 3-4 days  do not message to anyone if u do that , your account will ban instantly \n"
    "• do not create channel / group until 3 days \n"
    "• do not login again and again , whenever u login the acc in new device repeat these steps to prevent high risk of account ban \n"
    "• add your recovery mail , and 2 step verification pass after 24 hours\n"
    "• Virtual numbers can be recycled later, so the recovery email + 2-step PIN are your real protection.\n"
    "</blockquote>\n"
    "<blockquote expandable><i>⚠️ Follow these tips to keep your account safe and avoid bans , we do not give any guarantee or provide refunds , "
    "these details are shared with you so u can prevent your acc and there is no full guarantee that your wp acc will still survive  it is platform "
    "security system .. by following these steps risk of getting ban reduces a lot.</i></blockquote>")


class OTPState(StatesGroup):
    waiting_service_search = State()
    waiting_country_search = State()


def stock_dot(n):
    return "🟢" if n >= 50 else ("🟡" if n >= 10 else "🔴")


def back_for(name):
    return "back_main" if is_wa(name) else "s3_user_root"


def busy_kb(retry_cb, back_cb):
    return KB([B("🔄 Try again", retry_cb)], [B("⬅️ Back", back_cb)])


async def gate(cq, sid=None):
    """service ON/OFF switches from the admin panel: 'wa' for WhatsApp, 'otp' for every other app."""
    name = ""
    if sid:
        cat = await s3_catalog()
        name = (cat or {}).get(sid, {}).get("name", "")
    key = "wa" if is_wa(name) else "otp"
    if not await service_on(key):
        await cq.answer("⚠️ This service is under maintenance. Please try again later!", show_alert=True)
        return False
    return True


# ===================== root =====================
async def render_root(target):
    cat = await s3_catalog()
    if not cat:
        return await edit(target, BUSY_TXT, KB([B("🔄 Try again", "s3_user_root")], [B("⬅️ Back", "back_main")]))
    pinned, seen = [], set()
    for label, wanted in (("📱 Telegram", "Telegram"), ("💬 WhatsApp", "WhatsApp")):
        sid = find_service(cat, wanted)
        if sid and sid not in seen:
            pinned.append((label, sid)); seen.add(sid)
    for wanted in POPULAR:
        if len(pinned) >= 9:
            break
        sid = next((s for s, e in cat.items() if norm(e["name"]) == norm(wanted)), None)
        if sid and sid not in seen:
            pinned.append((wanted, sid)); seen.add(sid)
    text = ("❤️‍🔥 <b>VTH PANEL</b><b> SMS &amp; Virtual Number Activation</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<blockquote>⚡ <b>{len(cat):,}+</b> apps &amp; platforms .\n"
            "🌍 Numbers from many countries, live stock &amp; prices .\n"
            "💯 <b>Auto refund</b> if no SMS arrives.\n"
            "🚀 OTP delivered straight into this chat.</blockquote>\n"
            "⭐ <b>Popular Services:</b>")
    rows = chunk([B(label, f"s3s:{sid}:0") for label, sid in pinned], 2)
    rows.append([B(f"🔎 Search All {len(cat):,} Services", "s3q")])
    rows.append([B("📂 Browse All Services", "s3pg:0"), B("ℹ️ Help", "s3help")])
    rows.append([B("⬅️ Back", "back_main")])
    await edit(target, text, KB(*rows))


@router.callback_query(F.data == "s3_user_root")
async def user_root(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await service_on("otp"):
        return await cq.answer("⚠️ Server 3 is under maintenance. Please try again later!", show_alert=True)
    await cq.answer()
    await render_root(cq)


@router.callback_query(F.data == "s3help")
async def help_cb(cq: CallbackQuery):
    await cq.answer()
    await edit(cq,
        "ℹ️ <b>About Server 3 / VTH panel Virtual Number Activation</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>What Services Are Provided?</b>\nFresh, private, disposable mobile numbers across <b>200+ countries</b> "
        "to receive SMS verification codes &amp; OTPs.\n\n"
        "<b>Key Capabilities &amp; Highlights:</b>\n"
        "• 📱 <b>Telegram:</b> change your account number or register fresh accounts with clean foreign numbers.\n"
        "• 💬 <b>WhatsApp &amp; WA Business:</b> instant verification codes.\n"
        "• 💡 <b>AI &amp; Cloud:</b> OpenAI, ChatGPT, Claude, Google Cloud, AWS, Microsoft.\n"
        "• 🌐 <b>Social Networks:</b> Instagram, Threads, TikTok, Twitter / X, Discord, Facebook, Snapchat, Reddit.\n"
        "• 💰 <b>Shopping &amp; Finance:</b> Amazon, Netflix, Steam, Tinder, Uber, Binance, PayPal.\n\n"
        "🛡️ <b>100% Zero-Risk Money-Back Guarantee:</b>\n"
        "<blockquote>• Numbers are allocated for <b>5 minutes</b>.\n"
        "• If no SMS arrives within 5 minutes, the order is automatically cancelled and your wallet is <b>100% refunded</b>.\n"
        "• You can also cancel manually after <b>3 minutes</b> if needed.</blockquote>",
        KB([B("⬅️ Back", "s3_user_root")]))


@router.callback_query(F.data == "s3n")
async def noop(cq: CallbackQuery):
    await cq.answer()


# ===================== browse / search services =====================
async def render_browse(target, page):
    cat = await s3_catalog()
    if not cat:
        return await edit(target, BUSY_TXT, KB([B("⬅️ Back", "s3_user_root")]))
    items = sorted(cat.items(), key=lambda kv: kv[1]["name"].lower())
    pages = max(1, (len(items) + PER_SERVICES - 1) // PER_SERVICES)
    page = max(0, min(page, pages - 1))
    chunk_ = items[page * PER_SERVICES:(page + 1) * PER_SERVICES]
    text = (f"📂 <b>All Available Services ({len(items):,} total)</b>\n<i>Page {page + 1} of {pages}</i>\n"
            "Tap any service to see countries &amp; live pricing:")
    rows = chunk([B(e["name"][:28], f"s3s:{sid}:0") for sid, e in chunk_], 2)
    nav = []
    if page > 0:
        nav.append(B("◀️ Prev", f"s3pg:{page - 1}"))
    nav.append(B(f"{page + 1}/{pages}", "s3n"))
    if page < pages - 1:
        nav.append(B("Next ▶️", f"s3pg:{page + 1}"))
    rows.append(nav)
    rows.append([B("🔎 Search", "s3q"), B("⬅️ Back", "s3_user_root")])
    await edit(target, text, KB(*rows))


@router.callback_query(F.data.startswith("s3pg:"))
async def browse_cb(cq: CallbackQuery):
    if not await service_on("otp"):
        return await cq.answer("⚠️ Server 3 is under maintenance.", show_alert=True)
    await cq.answer()
    await render_browse(cq, int(cq.data.split(":")[1]))


@router.callback_query(F.data == "s3q")
async def search_prompt(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    await state.set_state(OTPState.waiting_service_search)
    await edit(cq, "🔎 <b>Search Any Service</b>\n\nSend the name of the app you want to activate.\n"
                   "<i>Example: whatsapp, telegram, instagram, openai…</i>",
               KB([B("✖️ Cancel Search", "s3_user_root")]))


@router.message(StateFilter(OTPState.waiting_service_search), F.text, ~F.text.startswith("/"))
async def search_text(msg: Message, state: FSMContext):
    await state.clear()
    cat = await s3_catalog()
    if not cat:
        return await msg.answer(BUSY_TXT, parse_mode="HTML")
    hits = search_services(cat, msg.text.strip(), 16)
    if not hits:
        return await msg.answer("❌ <b>No service found.</b> Try another name.", parse_mode="HTML",
                                reply_markup=KB([B("🔎 Search Again", "s3q")], [B("⬅️ Back", "s3_user_root")]))
    rows = chunk([B(e["name"][:28], f"s3s:{sid}:0") for sid, e in hits], 2)
    rows.append([B("🔎 Search Again", "s3q"), B("⬅️ Back", "s3_user_root")])
    await msg.answer(f"🔎 <b>Results for '{esc(msg.text.strip()[:40])}'</b>\n<i>Tap a service:</i>",
                     parse_mode="HTML", reply_markup=KB(*rows))


# ===================== countries =====================
async def render_countries(target, sid, page=0, query=None, full=False):
    cat = await s3_catalog()
    svc = (cat or {}).get(sid)
    if not svc:
        return await render_root(target)
    title = esc(svc["name"])
    back = back_for(svc["name"])
    await edit(target, f"⏳ <i>Fetching live rates for {title}…</i>")
    rows = await s3_countries(sid, full=full)
    if rows is None:
        return await edit(target, f"<b>Service: {title}</b>\n{LINE}\n{BUSY_TXT}", busy_kb(f"s3r:{sid}", back))
    if query:
        q = query.lower().strip()
        rows = [r for r in rows if q in r["name"].lower()]
    if not rows:
        kb_rows = []
        if query:
            kb_rows.append([B("🔎 Search Again", f"s3cq:{sid}")])
        elif not full:
            kb_rows.append([B("🌍 All Countries", f"s3a:{sid}:0")])
        kb_rows.append([B("⬅️ Back", f"s3s:{sid}:0" if query else back)])
        msg = "❌ No matching country in stock." if query else "📭 <b>Out of stock</b> — no numbers for this service right now."
        return await edit(target, f"<b>Service: {title}</b>\n{LINE}\n{msg}", KB(*kb_rows))
    pages = max(1, (len(rows) + PER_COUNTRIES - 1) // PER_COUNTRIES)
    page = max(0, min(page, pages - 1))
    shown = rows if query else rows[page * PER_COUNTRIES:(page + 1) * PER_COUNTRIES]
    text = (f"📦 <b>Service: {title}</b>\n{LINE}\n"
            "Select a country to view available virtual numbers &amp; live rates:\n"
            f"<i>{len(rows)} countries in stock</i>")
    if norm(svc["name"]) == "telegram":
        text = TELEGRAM_NOTE + "\n\n" + text
    pfx = "s3a" if full else "s3s"
    kb_rows = chunk([B(f"{flag_for(r['name'])} {r['name'][:20]} · {fmt_short(r['my_price'])}", f"s3c:{sid}:{r['country']}")
                     for r in shown], 2)
    if not query and pages > 1:
        nav = []
        if page > 0:
            nav.append(B("◀️", f"{pfx}:{sid}:{page - 1}"))
        nav.append(B(f"{page + 1}/{pages}", "s3n"))
        if page < pages - 1:
            nav.append(B("▶️", f"{pfx}:{sid}:{page + 1}"))
        kb_rows.append(nav)
    kb_rows.append([B("🔎 Search Country", f"s3cq:{sid}"), B("🔄 Refresh", f"s3r:{sid}")])
    if not full and not query:
        kb_rows.append([B("🌍 All Countries", f"s3a:{sid}:0")])
    kb_rows.append([B("⬅️ Back", back)])
    await edit(target, text, KB(*kb_rows))


@router.callback_query(F.data.startswith("s3s:"))
async def countries_cb(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    _, sid, page = cq.data.split(":")
    if not await gate(cq, sid):
        return
    await cq.answer()
    await render_countries(cq, sid, int(page))


@router.callback_query(F.data.startswith("s3a:"))
async def countries_full_cb(cq: CallbackQuery):
    _, sid, page = cq.data.split(":")
    if not await gate(cq, sid):
        return
    await cq.answer()
    await render_countries(cq, sid, int(page), full=True)


@router.callback_query(F.data.startswith("s3r:"))
async def refresh_cb(cq: CallbackQuery):
    sid = cq.data.split(":")[1]
    if not await gate(cq, sid):
        return
    drop_s3_cache(sid)
    await cq.answer("🔄 Updated")
    cat = await s3_catalog()
    await render_countries(cq, sid, 0, full=is_wa((cat or {}).get(sid, {}).get("name")))


@router.callback_query(F.data.startswith("s3cq:"))
async def country_search_prompt(cq: CallbackQuery, state: FSMContext):
    sid = cq.data.split(":")[1]
    await cq.answer()
    await state.set_state(OTPState.waiting_country_search)
    await state.update_data(sid=sid)
    await edit(cq, "🔎 <b>Search Country</b>\n\nSend a country name (e.g. <code>India</code>, <code>Brazil</code>):",
               KB([B("✖️ Cancel", f"s3s:{sid}:0")]))


@router.message(StateFilter(OTPState.waiting_country_search), F.text, ~F.text.startswith("/"))
async def country_search_text(msg: Message, state: FSMContext):
    sid = (await state.get_data()).get("sid")
    await state.clear()
    if not sid:
        return
    screen = await msg.answer("⏳ <i>Searching…</i>", parse_mode="HTML")
    await render_countries(screen, sid, 0, query=msg.text.strip(), full=True)


# ===================== operators / confirm =====================
async def render_operators(target, sid, cid, note=None):
    cat = await s3_catalog()
    svc = (cat or {}).get(sid)
    if not svc:
        return await render_root(target)
    off = await s3_offers(sid, cid)
    if off is None:
        return await edit(target, BUSY_TXT, busy_kb(f"s3c:{sid}:{cid}", f"s3s:{sid}:0"))
    cname, ops = off
    if not ops:
        return await render_countries(target, sid, 0)
    text = (f"📶 <b>Select Operator</b>\n{LINE}\n"
            f"• <b>Service:</b> {esc(svc['name'])}\n"
            f"• <b>Country:</b> {flag_for(cname)} {esc(cname)}\n"
            "<blockquote>Prices &amp; stock are live. 🔥 = best price. If an operator runs out, you will be told and brought back here.</blockquote>")
    if note:
        text = f"{note}\n\n{text}"
    rows = []
    for i, o in enumerate(ops):
        stock = f"{o['stock']}" if o["stock"] < 1000 else "999+"
        best = "🔥 " if i == 0 and len(ops) > 1 else ""
        rows.append([B(f"{best}{stock_dot(o['stock'])} Operator {o['operator']} · {fmt_short(o['my_price'])} · {stock} left",
                       f"s3o:{sid}:{cid}:{o['operator']}")])
    rows.append([B("🔄 Refresh", f"s3rc:{sid}:{cid}"), B("🌍 Change Country", f"s3s:{sid}:0")])
    rows.append([B("⬅️ Back", f"s3s:{sid}:0")])
    await edit(target, text, KB(*rows))


@router.callback_query(F.data.startswith("s3c:"))
async def operators_cb(cq: CallbackQuery):
    _, sid, cid = cq.data.split(":")
    if not await gate(cq, sid):
        return
    await cq.answer()
    await edit(cq, "⏳ <b>Loading operators…</b>\n<i>Fetching live rates, one moment.</i>")
    await render_operators(cq, sid, cid)


@router.callback_query(F.data.startswith("s3rc:"))
async def operators_refresh(cq: CallbackQuery):
    _, sid, cid = cq.data.split(":")
    drop_s3_cache(sid)
    await cq.answer("🔄 Updated")
    await render_operators(cq, sid, cid)


@router.callback_query(F.data.startswith("s3o:"))
async def confirm_cb(cq: CallbackQuery):
    _, sid, cid, op = cq.data.split(":")
    if not await gate(cq, sid):
        return
    await render_confirm(cq, sid, cid, op)


async def render_confirm(cq, sid, cid, op):
    cat = await s3_catalog()
    off = await s3_offers(sid, cid)
    if not cat or sid not in cat or off is None:
        return await render_operators(cq, sid, cid)
    cname, ops = off
    row = next((o for o in ops if str(o["operator"]) == str(op)), None)
    if not row:
        await cq.answer(f"❌ Operator {op} has no numbers right now.")
        return await render_operators(cq, sid, cid, note=f"⚠️ <b>Operator {op}</b> is out of stock.")
    await cq.answer()
    price = row["my_price"]
    bal = await get_balance(cq.from_user.id)
    enough = bal >= price
    text = (f"🛒 <b>Virtual Number Activation</b>\n{LINE}\n<blockquote>"
            f"• <b>Service:</b> {esc(cat[sid]['name'])}\n"
            f"• <b>Country:</b> {flag_for(cname)} {esc(cname)}\n"
            f"• <b>Operator:</b> Operator {op}\n"
            f"• <b>Available:</b> {row['stock']} numbers\n"
            f"• <b>Price:</b> {fmt_curr(price)}</blockquote>\n"
            f"💳 <b>Your balance:</b> {fmt_curr(bal)}"
            + (f"  →  after: {fmt_curr(bal - price)}\n" if enough else f"  ❌ short by {fmt_curr(price - bal)}\n") +
            "\n⚠️ <b>Rules</b>\n"
            f"• Number is reserved for {OTP_TIMEOUT // 60} minutes to receive your OTP\n"
            "• 100% auto refund if no SMS arrives\n"
            "• Non-refundable once the verification code has arrived\n"
            f"• Cancel unlocks after {CANCEL_LOCK // 60} minutes without OTP")
    buy_row = ([B(f"✅ Purchase — {fmt_short(price)}", f"s3b:{sid}:{cid}:{op}:{int(price) if price == int(price) else price}")]
               if enough else [B("💰 Recharge", "recharge")])
    await edit(cq, text, KB(buy_row, [B("🔁 Switch Operator", f"s3c:{sid}:{cid}"), B("🌍 Change Country", f"s3s:{sid}:0")]))


# ===================== buy =====================
def wait_view(task, left):
    left = max(0, int(left))
    filled = round(10 * left / OTP_TIMEOUT)
    bar = "▰" * filled + "▱" * (10 - filled)
    elapsed = OTP_TIMEOUT - left
    text = ("<blockquote>✅ <b>Number Reserved</b></blockquote>\n"
            f"{LINE}\n"
            f"📞 <b>Number:</b> <code>+{esc(task['phone'])}</code>\n"
            f"📦 <b>Service:</b> {esc(task['service'])}\n"
            f"🌍 <b>Country:</b> {flag_for(task['country'])} {esc(task['country'])} · Operator {esc(task['operator'])}\n"
            f"💬 <b>OTP:</b> <code>Waiting for message…</code>\n"
            f"⏱ <b>Time left:</b> {left // 60}:{left % 60:02d}  {bar}\n\n"
            "<blockquote expandable><i>The OTP is delivered here automatically. "
            f"Cancel unlocks after {CANCEL_LOCK // 60} minutes without OTP; "
            f"after {OTP_TIMEOUT // 60} minutes the order is cancelled and refunded automatically.</i></blockquote>")
    cancel_txt = f"🔒 Cancel in {int(CANCEL_LOCK - elapsed)}s" if elapsed < CANCEL_LOCK else "🛑 Cancel & Refund"
    return text, KB([B("📋 Copy Number", copy=f"+{task['phone']}")], [B(cancel_txt, f"s3x:{task['order_id']}")])


def end_kb(task):
    return KB([B("🔄 Buy Again", f"s3o:{task['sid']}:{task['country_id']}:{task['operator']}")],
              [B("⬅️ Menu", back_for(task["service"]))])


async def _edit_task(task, text, kb=None):
    bot = get_bot()
    try:
        await bot.edit_message_text(text, chat_id=task["chat_id"], message_id=task["msg_id"],
                                    reply_markup=kb, parse_mode="HTML", link_preview_options=NOPREV)
    except Exception as e:
        if "not modified" not in str(e).lower():
            print(f"[otp] edit failed: {e}")


async def show_completed(task, otp):
    kb = KB([B("📋 Copy OTP", copy=otp)],
            [B("🔄 Buy Again", f"s3o:{task['sid']}:{task['country_id']}:{task['operator']}"),
             B("⬅️ Menu", back_for(task["service"]))])
    await _edit_task(task, "✅ <b>Order Completed</b>\n━━━━━━━━━━━━━━━━━━━━\n"
                           f"📞 <b>Number:</b> <code>+{esc(task['phone'])}</code>\n"
                           f"📦 <b>Service:</b> {esc(task['service'])}\n"
                           f"🌍 <b>Country:</b> {flag_for(task['country'])} {esc(task['country'])} · Operator {esc(task['operator'])}\n"
                           f"💬 <b>OTP:</b> <code>{esc(otp)}</code>", kb)
    if is_wa(task["service"]):
        try:
            await get_bot().send_message(task["chat_id"], WHATSAPP_TIPS, parse_mode="HTML")
        except Exception:
            pass


async def show_cancelled(task, why="⏱ <b>No OTP received.</b> Order cancelled."):
    await _edit_task(task, f"{why}\n💰 <b>Refunded:</b> {fmt_curr(task['price'])}", end_kb(task))


@router.callback_query(F.data.startswith("s3b:"))
async def buy_cb(cq: CallbackQuery):
    _, sid, cid, op, shown = cq.data.split(":")
    if not await gate(cq, sid):
        return
    if is_spamming(cq.from_user.id, "s3buy", 4):
        return await cq.answer("⏳ Please wait a few seconds…")
    await cq.answer()
    await edit(cq, "⏳ <i>Assigning your number…</i>")
    r = await buy_s3(cq.from_user.id, sid, cid, op, float(shown), cq.message.chat.id, cq.message.message_id)
    k = r["kind"]
    if k == "ok":
        text, kb = wait_view(r["task"], OTP_TIMEOUT)
        return await edit(cq, text, kb)
    if k == "price":
        await cq.message.answer(f"ℹ️ Price changed to <b>{fmt_short(r['price'])}</b>. Please confirm again.", parse_mode="HTML")
        return await render_confirm(cq, sid, cid, op)
    if k == "funds":
        return await edit(cq, f"❌ <b>Insufficient balance</b>\nYou need <b>{fmt_curr(r['need'])}</b> more.",
                          KB([B("💰 Recharge", "recharge")], [B("⬅️ Back", f"s3c:{sid}:{cid}")]))
    if k == "stock":
        drop_s3_cache(sid)
        return await render_operators(cq, sid, cid, note=f"⚠️ <b>Operator {op}</b> is out of stock.")
    await edit(cq, r["text"])
    await asyncio.sleep(1.5)
    await render_operators(cq, sid, cid)


@router.callback_query(F.data.startswith("s3x:"))
async def cancel_cb(cq: CallbackQuery):
    oid = cq.data.split(":", 1)[1]
    r = await s3_cancel(cq.from_user.id, oid)
    k = r["kind"]
    if k == "locked":
        return await cq.answer(f"🔒 You can cancel after {CANCEL_LOCK // 60} minutes without OTP. ({r['left']}s left)", show_alert=True)
    if k == "gone":
        return await cq.answer("This order is already finished.", show_alert=True)
    if k == "cancelled":
        await cq.answer("✅ Cancelled & refunded")
        return await show_cancelled(r["task"], "🛑 <b>Order cancelled.</b>")
    if k == "completed":
        await cq.answer()
        if r.get("won"):
            await show_completed(r["task"], r.get("otp"))
        return
    await cq.answer("⚠️ Server busy. Try again in a moment.", show_alert=True)


# ===================== WhatsApp accounts =====================
@router.callback_query(F.data == "wp_terms")
async def wp_terms(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await service_on("wa"):
        return await cq.answer("⚠️ WhatsApp is under maintenance. Please try again later!", show_alert=True)
    text = ("💬 <b>WhatsApp Account — Terms &amp; Conditions</b>\n––––––—–————––––——–––•\n"
            "<blockquote>These are <b>not ready-made accounts</b> — a <b>fresh new number</b> will be provided from the panel.\n\n"
            "Sometimes you may get an account on your very first buy, and sometimes you may need to try multiple times. "
            "There are a lot of issues because of WhatsApp's security system.\n\n"
            "For a better experience and to avoid problems, please read the guide below, "
            "then click <b>Agree &amp; Continue</b> to proceed.</blockquote>")
    rows = []
    if WP_GUIDE_URL:
        rows.append([B("How to buy WP acc", url=WP_GUIDE_URL)])
    rows.append([B("Agree & Continue", "s3_open_wp")])
    rows.append([B("Cancel", "back_main")])
    await edit(cq, text, KB(*rows))
    await cq.answer()


@router.callback_query(F.data == "s3_open_wp")
async def open_whatsapp(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await service_on("wa"):
        return await cq.answer("⚠️ WhatsApp is under maintenance. Please try again later!", show_alert=True)
    await cq.answer()
    cat = await s3_catalog()
    sid = find_service(cat or {}, "WhatsApp")
    if not sid:
        return await edit(cq, "❌ WhatsApp is not available right now. Please try again later.",
                          KB([B("⬅️ Back", "back_main")]))
    await edit(cq, "⏳ <i>Opening WhatsApp…</i>")
    await render_countries(cq, sid, 0, full=True)


# ===================== background worker: OTP delivery / timeout / refunds =====================
_last_edit = {}


async def _check(task, sem):
    async with sem:
        try:
            r = await s3_poll(task)
            if r["act"] == "completed" and r["won"]:
                await show_completed(task, r["otp"])
            elif r["act"] == "cancelled" and r["won"]:
                await show_cancelled(task)
            elif r["act"] == "active":
                now = time.time()
                if now - _last_edit.get(task["order_id"], 0) >= 10:
                    _last_edit[task["order_id"]] = now
                    text, kb = wait_view(task, r["left"])
                    await _edit_task(task, text, kb)
        except Exception as e:
            print(f"[otp-loop] {task.get('order_id')}: {e!r}")


async def otp_loop():
    await asyncio.sleep(3)
    sem = asyncio.Semaphore(8)
    while True:
        active = []
        try:
            active = await tasks.find({"status": "active"}).to_list(300)
            if active:
                await asyncio.gather(*[_check(t, sem) for t in active])
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"[otp-loop] {e!r}")
        await asyncio.sleep(max(6, min(len(active) * 1.1, 30)) if active else 6)
