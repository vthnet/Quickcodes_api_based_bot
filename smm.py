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


"""Social media services  ->  runs on the Quick Codes SMM API."""
import asyncio
import re
import time
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from db import service_on, get_balance, smm_orders, profit_pct
from flows import (smm_catalog, smm_cost, buy_smm, smm_sync_order, smm_refill, needs_comments, is_package, with_profit)
from notify import get_bot
from utils import B, KB, esc, fmt_curr, short, edit, chunk, pager_row, SEP

router = Router()
PAGE_CATS, PAGE_SERVICES, PAGE_HISTORY = 10, 8, 6

APPS = [("telegram", "Telegram", "✈️"), ("instagram", "Instagram", "📸"), ("youtube", "YouTube", "▶️"),
        ("facebook", "Facebook", "📘"), ("tiktok", "TikTok", "🎵"), ("twitter", "Twitter / X", "🐦"),
        ("whatsapp", "WhatsApp", "💬"), ("spotify", "Spotify", "🎧"), ("snapchat", "Snapchat", "👻"),
        ("linkedin", "LinkedIn", "💼"), ("threads", "Threads", "🧵"), ("discord", "Discord", "🎮"),
        ("pinterest", "Pinterest", "📌"), ("twitch", "Twitch", "🟣"), ("reddit", "Reddit", "👽"),
        ("soundcloud", "SoundCloud", "☁️"), ("website", "Website / SEO", "🌐"), ("others", "Others", "📦")]
APP_META = {k: (n, e) for k, n, e in APPS}
STATUS_EMOJI = {"pending": "⏳", "in progress": "🔄", "processing": "🔄", "completed": "✅", "partial": "🟡",
                "canceled": "❌", "cancelled": "❌", "refunded": "↩️", "fail": "❌", "failed": "❌", "unconfirmed": "❔"}
FINAL = {"canceled", "cancelled", "refunded", "fail", "failed", "completed", "partial"}
BUSY = set()
_click = {}


class SMMState(StatesGroup):
    waiting_app_search = State()
    waiting_srv_search = State()
    waiting_link = State()
    waiting_quantity = State()
    waiting_comments = State()


def status_label(st):
    st = (st or "pending").lower()
    return f"{STATUS_EMOJI.get(st, '⏳')} {st.title()}"


def rate_label(srv, pct):
    r = with_profit(srv["rate"], pct)
    return f"{fmt_curr(r)} / package" if is_package(srv) else f"{fmt_curr(r)} per 1000"


async def need_catalog(cq):
    if not await service_on("smm"):
        await cq.answer("🛠 SMM Panel is under maintenance.", show_alert=True)
        return None
    cat = await smm_catalog()
    if not cat:
        await cq.answer("⚠️ Service catalog is unavailable right now. Try again shortly.", show_alert=True)
        return None
    return cat


async def render_main(target, uid):
    cat = await smm_catalog()
    apps = [(k, n, e) for k, n, e in APPS if k in cat["apps"]]
    text = (f"<b>🌍 SMM Panel</b>\n{SEP}\n"
            "<blockquote>• Growth services for every platform\n• Live rates · fast start · order tracking\n"
            "• Auto-refund to wallet if an order is cancelled</blockquote>\n"
            f"💳 <b>Wallet:</b> {fmt_curr(await get_balance(uid))}\n\n👇 <b>Select a platform or search:</b>")
    rows = chunk([B(f"{e} {n}", f"sm_app:{k}:0") for k, n, e in apps], 2)
    rows.append([B("Search App", "sm_sapp"), B("Search Services", "sm_ssrv")])
    rows.append([B("My Orders", "sm_hist:0")])
    rows.append([B("⬅️ Back", "back_main")])
    await edit(target, text, KB(*rows))


@router.callback_query(F.data == "feature_smm_external")
async def smm_main(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    if not await service_on("smm"):
        return await cq.answer("🛠 SMM Panel is under maintenance.", show_alert=True)
    await cq.answer()
    if not await smm_catalog():
        return await edit(cq, "⚠️ <b>Service catalog is unavailable right now.</b>\n<i>Please try again shortly.</i>",
                          KB([B("⬅️ Back", "back_main")]))
    await render_main(cq, cq.from_user.id)


@router.callback_query(F.data == "sm_noop")
async def noop(cq: CallbackQuery):
    await cq.answer()


# ---- app -> categories ----
@router.callback_query(F.data.startswith("sm_app:"))
async def app_view(cq: CallbackQuery, state: FSMContext):
    cat = await need_catalog(cq)
    if not cat:
        return
    _, slug, page = cq.data.split(":")
    page = int(page)
    cats = cat["apps"].get(slug)
    meta = APP_META.get(slug, (slug.title(), "📦"))
    if not cats:
        return await cq.answer("⚠️ No services available for this app.", show_alert=True)
    await state.update_data(back=cq.data)
    rows = [[B(f"{short(cn, 44)} ({len(v)})", f"sm_cat:{slug}:{i}:0")]
            for i, (cn, v) in enumerate(cats) if page * PAGE_CATS <= i < (page + 1) * PAGE_CATS]
    pr = pager_row(page, max(1, -(-len(cats) // PAGE_CATS)), lambda p: f"sm_app:{slug}:{p}", "sm_noop")
    if pr:
        rows.append(pr)
    rows.append([B(f"🔎 Search in {meta[0]}", f"sm_sin:{slug}")])
    rows.append([B("⬅️ Back to Apps", "feature_smm_external")])
    await edit(cq, f"<b>{meta[1]} {esc(meta[0])}</b>\n{SEP}\n<i>Select a category:</i>", KB(*rows))
    await cq.answer()


# ---- category -> services ----
@router.callback_query(F.data.startswith("sm_cat:"))
async def cat_view(cq: CallbackQuery, state: FSMContext):
    cat = await need_catalog(cq)
    if not cat:
        return
    _, slug, ci, page = cq.data.split(":")
    ci, page = int(ci), int(page)
    cats = cat["apps"].get(slug) or []
    if ci >= len(cats):
        return await cq.answer("⚠️ No services found.", show_alert=True)
    name, services = cats[ci]
    pct = await profit_pct("smm")
    await state.update_data(back=cq.data)
    rows = [[B(f"{fmt_curr(with_profit(s['rate'], pct))} · {short(s['name'], 40)}", f"sm_srv:{s['service']}")]
            for s in services[page * PAGE_SERVICES:(page + 1) * PAGE_SERVICES]]
    pr = pager_row(page, max(1, -(-len(services) // PAGE_SERVICES)), lambda p: f"sm_cat:{slug}:{ci}:{p}", "sm_noop")
    if pr:
        rows.append(pr)
    rows.append([B("⬅️ Back", f"sm_app:{slug}:0")])
    await edit(cq, f"<b>📂 {esc(short(name, 60))}</b>\n{SEP}\n"
                   f"<i>{len(services)} services · price per 1000 shown · cheapest first</i>", KB(*rows))
    await cq.answer()


# ---- search ----
@router.callback_query(F.data == "sm_sapp")
async def search_app_prompt(cq: CallbackQuery, state: FSMContext):
    await edit(cq, "🔍 <b>Send the app name to search:</b>\n<i>(e.g. instagram, telegram, youtube)</i>",
               KB([B("⬅️ Back", "feature_smm_external")]))
    await state.set_state(SMMState.waiting_app_search)
    await cq.answer()


@router.message(StateFilter(SMMState.waiting_app_search), F.text, ~F.text.startswith("/"))
async def search_app_results(msg: Message, state: FSMContext):
    await state.clear()
    cat = await smm_catalog()
    if not cat:
        return await msg.answer("⚠️ Service catalog unavailable. Try again later.")
    q = msg.text.strip().lower()
    matches = [(k, n, e) for k, n, e in APPS if k in cat["apps"] and (q in n.lower() or q in k)]
    if not matches:
        return await msg.answer("❌ <b>No app found.</b> Try another name.", parse_mode="HTML",
                                reply_markup=KB([B("🔍 Try Again", "sm_sapp")], [B("⬅️ Back to Apps", "feature_smm_external")]))
    rows = [[B(f"{e} {n}", f"sm_app:{k}:0")] for k, n, e in matches]
    rows.append([B("⬅️ Back to Apps", "feature_smm_external")])
    await msg.answer(f"🔍 <b>Apps matching '{esc(q)}':</b>", parse_mode="HTML", reply_markup=KB(*rows))


@router.callback_query(F.data.in_({"sm_ssrv"}) | F.data.startswith("sm_sin:"))
async def search_srv_prompt(cq: CallbackQuery, state: FSMContext):
    app = cq.data.split(":")[1] if cq.data.startswith("sm_sin:") else None
    await state.update_data(sapp=app)
    where = f" in <b>{esc(APP_META.get(app, (app,))[0])}</b>" if app else ""
    await edit(cq, f"🔎 <b>Send a keyword to search services{where}:</b>\n"
                   "<i>(e.g. likes, followers, views, instagram likes, or a service ID)</i>",
               KB([B("⬅️ Back", f"sm_app:{app}:0" if app else "feature_smm_external")]))
    await state.set_state(SMMState.waiting_srv_search)
    await cq.answer()


async def render_search(data, page):
    q, app = data.get("sq"), data.get("sapp")
    cat = await smm_catalog()
    pct = await profit_pct("smm")
    ql = (q or "").lower()
    res = [s for s in cat["services"].values()
           if (not app or (s.get("app") or "others") == app)
           and (ql in s["name"].lower() or ql in s["category"].lower() or ql == str(s["service"]))]
    res.sort(key=lambda s: s["rate"])
    if not res:
        return (f"❌ <b>No services found for '{esc(q)}'.</b>\n<i>Try a shorter keyword.</i>",
                KB([B("🔎 New Search", "sm_ssrv")], [B("⬅️ Back to Apps", "feature_smm_external")]), 0)
    pages = max(1, -(-len(res) // PAGE_SERVICES))
    page = min(max(page, 0), pages - 1)
    rows = [[B(f"{fmt_curr(with_profit(s['rate'], pct))} · {short(s['name'], 40)}", f"sm_srv:{s['service']}")]
            for s in res[page * PAGE_SERVICES:(page + 1) * PAGE_SERVICES]]
    pr = pager_row(page, pages, lambda p: f"ss:{p}", "sm_noop")
    if pr:
        rows.append(pr)
    rows.append([B("🔎 New Search", "sm_ssrv")])
    rows.append([B("⬅️ Back to Apps", "feature_smm_external")])
    return (f"🔎 <b>Results for '{esc(q)}'</b>\n{SEP}\n<i>{len(res)} services found · tap one to order</i>", KB(*rows), page)


@router.message(StateFilter(SMMState.waiting_srv_search), F.text, ~F.text.startswith("/"))
async def search_srv_results(msg: Message, state: FSMContext):
    if not await smm_catalog():
        return await msg.answer("⚠️ Service catalog unavailable. Try again later.")
    await state.set_state(None)
    await state.update_data(sq=msg.text.strip()[:50])
    text, kb, page = await render_search(await state.get_data(), 0)
    await state.update_data(back=f"ss:{page}")
    await msg.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("ss:"))
async def search_page(cq: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("sq"):
        return await cq.answer("⌛ Search expired. Search again.", show_alert=True)
    page = int(cq.data.split(":")[1])
    text, kb, page = await render_search(data, page)
    await state.update_data(back=f"ss:{page}")
    await edit(cq, text, kb)
    await cq.answer()


# ---- service details ----
@router.callback_query(F.data.startswith("sm_srv:"))
async def service_details(cq: CallbackQuery, state: FSMContext):
    cat = await need_catalog(cq)
    if not cat:
        return
    sid = cq.data.split(":")[1]
    srv = cat["services"].get(sid)
    if not srv:
        return await cq.answer("❌ This service is no longer available.", show_alert=True)
    pct = await profit_pct("smm")
    back = (await state.get_data()).get("back") or "feature_smm_external"
    limits = "Fixed package" if is_package(srv) else f"Min {srv['min']:,} / Max {srv['max']:,}"
    text = (f"<b>🛒 Service Details</b>\n{SEP}\n"
            f"<blockquote><b>📱 App:</b> {esc(APP_META.get(srv.get('app') or 'others', ('Others',))[0])}\n"
            f"<b>🏷️ Service:</b> {esc(srv['name'])}\n"
            f"<b>🆔 ID:</b> <code>{srv['service']}</code>\n"
            f"<b>📂 Category:</b> {esc(short(srv['category'], 60))}\n"
            f"<b>💰 Price:</b> {rate_label(srv, pct)}\n"
            f"<b>📊 Limits:</b> {limits}\n"
            f"<b>♻️ Refill:</b> {'Yes' if srv['refill'] else 'No'}</blockquote>\n\n"
            "❓ <b>Do you want to order this service?</b>")
    await edit(cq, text, KB([B("🛒 Order Now", f"sm_order:{sid}"), B("Back", back)]))
    await cq.answer()


# ---- order flow ----
def _cancel_kb(sid):
    return KB([B("Cancel", f"sm_srv:{sid}")])


@router.callback_query(F.data.startswith("sm_order:"))
async def order_start(cq: CallbackQuery, state: FSMContext):
    cat = await need_catalog(cq)
    if not cat:
        return
    sid = cq.data.split(":")[1]
    if sid not in cat["services"]:
        return await cq.answer("❌ This service is no longer available.", show_alert=True)
    await state.update_data(sid=sid, link=None, qty=None, comments=None, cost=None)
    await edit(cq, "🔗 <b>Please send the target link:</b>\n<i>(Profile / post / channel URL - make sure it is PUBLIC)</i>",
               _cancel_kb(sid))
    await state.set_state(SMMState.waiting_link)
    await cq.answer()


@router.message(StateFilter(SMMState.waiting_link), F.text, ~F.text.startswith("/"))
async def got_link(msg: Message, state: FSMContext):
    link = msg.text.strip()
    if len(link) < 3 or len(link) > 500 or re.search(r"\s", link):
        return await msg.answer("❌ <b>Invalid link.</b> Send a single link/username without spaces.", parse_mode="HTML")
    cat = await smm_catalog()
    srv = (cat or {}).get("services", {}).get((await state.get_data()).get("sid"))
    if not srv:
        await state.clear()
        return await msg.answer("⌛ Session expired. Please select the service again.")
    await state.update_data(link=link)
    if needs_comments(srv):
        await msg.answer("💬 <b>Send your custom comments</b> - one comment per line.\n"
                         + ("" if is_package(srv) else f"<i>(Min {srv['min']} / Max {srv['max']} comments)</i>"),
                         parse_mode="HTML", reply_markup=_cancel_kb(srv["service"]))
        await state.set_state(SMMState.waiting_comments)
    elif is_package(srv):
        await state.update_data(qty=1)
        await send_overview(msg, state, msg.from_user.id)
    else:
        await msg.answer(f"🔢 <b>Enter Quantity:</b>\n<i>(Min: {srv['min']:,} | Max: {srv['max']:,})</i>",
                         parse_mode="HTML", reply_markup=_cancel_kb(srv["service"]))
        await state.set_state(SMMState.waiting_quantity)


@router.message(StateFilter(SMMState.waiting_quantity), F.text, ~F.text.startswith("/"))
async def got_quantity(msg: Message, state: FSMContext):
    raw = msg.text.strip().replace(",", "")
    if not raw.isdigit():
        return await msg.answer("❌ Invalid number. Please enter a valid quantity.")
    qty = int(raw)
    cat = await smm_catalog()
    srv = (cat or {}).get("services", {}).get((await state.get_data()).get("sid"))
    if not srv:
        await state.clear()
        return await msg.answer("⌛ Session expired. Please select the service again.")
    if qty < srv["min"] or qty > srv["max"]:
        return await msg.answer(f"❌ Quantity out of limits ({srv['min']:,} - {srv['max']:,}). Try again.")
    await state.update_data(qty=qty)
    await send_overview(msg, state, msg.from_user.id)


@router.message(StateFilter(SMMState.waiting_comments), F.text, ~F.text.startswith("/"))
async def got_comments(msg: Message, state: FSMContext):
    lines = [l.strip() for l in msg.text.splitlines() if l.strip()]
    cat = await smm_catalog()
    srv = (cat or {}).get("services", {}).get((await state.get_data()).get("sid"))
    if not srv:
        await state.clear()
        return await msg.answer("⌛ Session expired. Please select the service again.")
    if not lines:
        return await msg.answer("❌ Send at least one comment.")
    qty = 1 if is_package(srv) else len(lines)
    if not is_package(srv) and (qty < srv["min"] or qty > srv["max"]):
        return await msg.answer(f"❌ You sent {qty} comments. Allowed: {srv['min']} - {srv['max']}.")
    await state.update_data(qty=qty, comments="\n".join(lines))
    await send_overview(msg, state, msg.from_user.id)


async def send_overview(msg, state, uid):
    data = await state.get_data()
    cat = await smm_catalog()
    srv = (cat or {}).get("services", {}).get(data.get("sid"))
    if not srv:
        await state.clear()
        return await msg.answer("⌛ Session expired. Please select the service again.")
    qty = data["qty"]
    cost = smm_cost(srv, qty, await profit_pct("smm"))
    await state.update_data(cost=cost)
    await state.set_state(None)
    bal = await get_balance(uid)
    qty_line = "Package" if is_package(srv) else f"{qty:,}" + (" comments" if needs_comments(srv) else "")
    warn = f"\n⚠️ <b>Insufficient wallet balance.</b> You need {fmt_curr(cost - bal)} more.\n" if bal < cost else ""
    text = (f"<b>📝 Order Overview</b>\n{SEP}\n"
            f"<blockquote><b>🏷️ Service:</b> {esc(srv['name'])}\n<b>🔗 Link:</b> {esc(data['link'])}\n"
            f"<b>🔢 Quantity:</b> {qty_line}\n<b>💰 Total Cost:</b> {fmt_curr(cost)}\n"
            f"<b>💳 Wallet:</b> {fmt_curr(bal)}</blockquote>{warn}\n"
            "<b>⚠️ Terms</b>\n<blockquote>• Link/profile must be PUBLIC.\n"
            "• Don't place multiple orders on the same link at once.\n"
            "• Cancelled/failed orders are refunded to your wallet automatically; "
            "partial orders are refunded for the undelivered part.</blockquote>")
    await msg.answer(text, parse_mode="HTML", reply_markup=KB([B("✅ Accept & Pay", "sm_exec"), B("Cancel", f"sm_srv:{srv['service']}")]))


@router.callback_query(F.data == "sm_exec")
async def exec_order(cq: CallbackQuery, state: FSMContext):
    uid = cq.from_user.id
    now = time.time()
    if uid in BUSY:
        return await cq.answer("⏳ Your order is still being processed.", show_alert=True)
    if now - _click.get(uid, 0) < 3:
        return await cq.answer("❄️ Please wait 3 seconds before clicking again.", show_alert=True)
    _click[uid] = now
    if not await service_on("smm"):
        return await cq.answer("🛠 SMM Panel is under maintenance.", show_alert=True)
    data = await state.get_data()
    if not data.get("sid") or not data.get("link") or not data.get("qty") or not data.get("cost"):
        await state.clear()
        return await cq.answer("⌛ Session expired. Please start the order again.", show_alert=True)
    BUSY.add(uid)
    try:
        await cq.answer()
        await edit(cq, "🔄 <i>Placing order on SMM Panel...</i>")
        r = await buy_smm(uid, data["sid"], data["link"], data["qty"], data.get("comments"), data["cost"])
    finally:
        BUSY.discard(uid)
    k = r["kind"]
    if k == "ok":
        o = r["order"]
        qty_txt = "Package" if o.get("package") else format(o["qty"], ",")
        await state.clear()
        return await edit(cq,
            f"<b>✅ Order Confirmed!</b>\n{SEP}\n"
            f"<blockquote><b>🆔 Order ID:</b> <code>{o['order_id']}</code>\n<b>🏷️ Service:</b> {esc(o['service'])}\n"
            f"<b>🔢 Qty:</b> {qty_txt}\n"
            f"<b>💸 Paid:</b> {fmt_curr(o['cost'])}</blockquote>\n\n"
            "⚠️ <i>Status updates can take a few minutes. If the order is cancelled, your wallet is refunded automatically.</i>",
            KB([B("🔄 Refresh Status", f"sm_ord:{o['order_id']}")], [B("📜 My Orders", "sm_hist:0"), B("🏠 Home", "back_main")]))
    if k == "unconfirmed":
        await state.clear()
        return await edit(cq, "⏳ <b>Order is being verified</b>\nThe server did not confirm in time. We are checking it — "
                              "if the order does not exist you will be refunded automatically.",
                          KB([B("📜 My Orders", "sm_hist:0"), B("🏠 Home", "back_main")]))
    if k == "price":
        await cq.message.answer(f"ℹ️ Price changed to <b>{fmt_curr(r['price'])}</b>. Please start the order again.", parse_mode="HTML")
        return await edit(cq, "Please select the service again.", KB([B("⬅️ Back", "feature_smm_external")]))
    if k == "funds":
        return await edit(cq, f"❌ <b>Insufficient balance.</b> You need {fmt_curr(r['need'])} more.",
                          KB([B("💰 Recharge", "recharge")], [B("⬅️ Back", "feature_smm_external")]))
    await edit(cq, f"❌ <b>Order failed</b>\n{r['text']}", KB([B("⬅️ Back", "feature_smm_external")]))


# ---- history / tracking ----
@router.callback_query(F.data.startswith("sm_hist:"))
async def history(cq: CallbackQuery):
    uid = cq.from_user.id
    page = int(cq.data.split(":")[1])
    total = await smm_orders.count_documents({"user_id": uid})
    if not total:
        return await cq.answer("❌ No SMM orders found yet.", show_alert=True)
    pages = max(1, -(-total // PAGE_HISTORY))
    page = min(max(page, 0), pages - 1)
    rows_ = await smm_orders.find({"user_id": uid}).sort("date", -1).skip(page * PAGE_HISTORY).limit(PAGE_HISTORY).to_list(PAGE_HISTORY)
    rows = []
    for o in rows_:
        em = STATUS_EMOJI.get((o.get("status") or "").lower(), "🧾")
        oid = o.get("order_id")
        rows.append([B(f"{em} #{oid if oid is not None else 'pending'} · {short(o.get('service', ''), 30)}",
                       f"sm_ord:{oid}" if oid is not None else "sm_noop")])
    pr = pager_row(page, pages, lambda p: f"sm_hist:{p}", "sm_noop")
    if pr:
        rows.append(pr)
    rows.append([B("Back", "feature_smm_external")])
    await edit(cq, f"📜 <b>Your SMM Orders</b>\n{SEP}\n<i>{total} orders · tap an order to track it or request a refill.</i>", KB(*rows))
    await cq.answer()


def order_view(o):
    st = (o.get("status") or "unknown").lower()
    d = o.get("date")
    lines = [f"<b>🏷️ Service:</b> {esc(o.get('service', 'Unknown'))}", f"<b>🔗 Link:</b> {esc(o.get('link', ''))}",
             f"<b>🔢 Quantity:</b> {'Package' if o.get('package') else format(o.get('qty') or 0, ',')}", f"<b>💰 Cost:</b> {fmt_curr(o.get('cost', 0))}",
             f"<b>📌 Status:</b> {status_label(st)}",
             f"<b>📈 Start Count:</b> {o.get('start_count') if o.get('start_count') is not None else 0}",
             f"<b>⏳ Remains:</b> {o.get('remains') if o.get('remains') is not None else 'N/A'}",
             f"<b>📅 Date:</b> {d.strftime('%Y-%m-%d %H:%M') if d else 'Unknown'}"]
    if o.get("refunded") and o.get("refund_amount"):
        lines.append(f"<b>↩️ Refunded:</b> {fmt_curr(o['refund_amount'])} (added to wallet)")
    if o.get("refill_id"):
        lines.append(f"<b>♻️ Refill ID:</b> {esc(o['refill_id'])}")
    text = (f"<b>📦 Order #{o['order_id']}</b>\n{SEP}\n<blockquote>" + "\n".join(lines) + "</blockquote>\n"
            "<i>Status can take a few minutes to update.</i>")
    rows = [[B("🔄 Refresh", f"sm_ord:{o['order_id']}")]]
    if o.get("can_refill") and st in ("completed", "partial"):
        rows.append([B("♻️ Request Refill", f"sm_refill:{o['order_id']}")])
    rows.append([B("My Orders", "sm_hist:0")])
    return text, KB(*rows)


async def _find(uid, oid):
    if not oid.lstrip("-").isdigit():
        return None
    return await smm_orders.find_one({"user_id": uid, "order_id": int(oid)})


@router.callback_query(F.data.startswith("sm_ord:"))
async def order_detail(cq: CallbackQuery):
    o = await _find(cq.from_user.id, cq.data.split(":")[1])
    if not o:
        return await cq.answer("❌ Order not found.", show_alert=True)
    st = (o.get("status") or "").lower()
    needs_refund_sync = st in ("canceled", "cancelled", "partial", "failed", "fail") and not o.get("refunded")
    if st not in FINAL or needs_refund_sync:
        o, _ = await smm_sync_order(o)
    text, kb = order_view(o)
    await edit(cq, text, kb)
    await cq.answer(f"📌 {(o.get('status') or 'pending').title()} · Remains: {o.get('remains', 'N/A')}")


@router.callback_query(F.data.startswith("sm_refill:"))
async def order_refill(cq: CallbackQuery):
    o = await _find(cq.from_user.id, cq.data.split(":")[1])
    if not o or not o.get("can_refill"):
        return await cq.answer("❌ Refill is not available for this order.", show_alert=True)
    ok, msg = await smm_refill(o)
    o = await smm_orders.find_one({"_id": o["_id"]}) or o
    text, kb = order_view(o)
    await edit(cq, text, kb)
    await cq.answer(msg[:190], show_alert=True)


# ---- background: keep orders in sync + refund users automatically ----
async def smm_loop():
    await asyncio.sleep(10)
    while True:
        try:
            pending = await smm_orders.find({"order_id": {"$ne": None}, "status": {"$nin": list(FINAL)}}).sort("date", -1).limit(200).to_list(200)
            for o in pending:
                fresh, got = await smm_sync_order(o)
                if got > 0:
                    try:
                        await get_bot().send_message(
                            o["user_id"], f"↩️ <b>Order #{o['order_id']}</b> was {str(fresh.get('status')).title()}.\n"
                                          f"💰 <b>{fmt_curr(got)}</b> has been refunded to your wallet.", parse_mode="HTML")
                    except Exception:
                        pass
                await asyncio.sleep(0.3)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"[smm-loop] {e!r}")
        await asyncio.sleep(120)
