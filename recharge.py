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

"""Wallet recharge: Auto UPI (UTR verification) and Manual UPI (admin approval)."""
import asyncio
import re
from io import BytesIO
from urllib.parse import quote
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from config import ADMIN_IDS, BOT_TITLE, SUPPORT_LINK
from db import get_settings, txns, users, utcnow
import payments
from payments import MIN_AUTO_UPI, MAX_AUTO_UPI, VERIFY_ATTEMPTS, VERIFY_GAP
from notify import get_bot
from utils import B, KB, esc, fmt_curr, edit, normalize_support, SEP

router = Router()


class RC(StatesGroup):
    auto_amount = State()
    auto_utr = State()
    claim_shot = State()
    manual_amount = State()
    manual_shot = State()


async def _replace(cq, text=None, kb=None, photo=None):
    """delete the old screen (it may be a photo) and send a fresh one"""
    try:
        await cq.message.delete()
    except Exception:
        pass
    if photo is not None:
        return await cq.message.answer_photo(photo, caption=text, reply_markup=kb, parse_mode="HTML")
    return await cq.message.answer(text, reply_markup=kb, parse_mode="HTML")


def make_qr(upi_id, amount):
    import qrcode
    link = f"upi://pay?pa={upi_id}&pn={quote(BOT_TITLE)}&am={amount:g}&cu=INR&tn=Wallet%20Recharge"
    qr = qrcode.QRCode(box_size=10, border=3)
    qr.add_data(link)
    qr.make(fit=True)
    bio = BytesIO()
    qr.make_image(fill_color="black", back_color="white").convert("RGB").save(bio, "PNG")
    return BufferedInputFile(bio.getvalue(), "pay.png")


def parse_amount(text):
    try:
        v = float(text.strip().replace("₹", "").replace(",", ""))
    except Exception:
        return None
    return round(v, 2) if v > 0 else None


async def menu_view():
    s = await get_settings()
    auto = s["auto_upi_active"] and s["AUTO_UPI_ID"] and s["UTR_API_MAIL"] and s["UTR_API_PASS"]
    manual = s["manual_upi_active"] and (s["MANUAL_UPI_ID"] or s["MANUAL_QR_FILE_ID"])
    rows = []
    if auto:
        rows.append([B("UPI (Auto)", "rc:auto")])
    if manual:
        rows.append([B("UPI (Manual)", "rc:manual")])
    rows.append([B("Back", "back_main")])
    if not (auto or manual):
        return "⚠️ <b>Recharge is currently unavailable.</b>\n<i>Please try again later.</i>", KB(*rows)
    return f"💳 <b>Recharge Wallet</b>\n{SEP}\n<i>Select a payment method:</i>", KB(*rows)


@router.callback_query(F.data == "recharge")
async def recharge(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    text, kb = await menu_view()
    await cq.answer()
    await _replace(cq, text, kb)


# =============================== AUTO UPI ===============================
@router.callback_query(F.data == "rc:auto")
async def auto_start(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    await state.set_state(RC.auto_amount)
    await _replace(cq, f"💰 <b>Enter the amount to add</b>\n<i>Minimum ₹{MIN_AUTO_UPI} · Maximum ₹{MAX_AUTO_UPI:,}</i>",
                   KB([B("Back", "recharge")]))


@router.message(StateFilter(RC.auto_amount), F.text, ~F.text.startswith("/"))
async def auto_amount(msg: Message, state: FSMContext):
    amt = parse_amount(msg.text)
    if amt is None or amt < MIN_AUTO_UPI or amt > MAX_AUTO_UPI:
        return await msg.answer(f"❌ Enter a valid amount between ₹{MIN_AUTO_UPI} and ₹{MAX_AUTO_UPI:,}.")
    s = await get_settings()
    await state.clear()
    await state.update_data(amount=amt)
    cap = (f"💳 <b>Pay ₹{amt:g}</b>\n{SEP}\n"
           f"<blockquote>Scan the QR with any UPI app, or pay to:\n<code>{esc(s['AUTO_UPI_ID'])}</code></blockquote>\n"
           f"⚠️ Pay <b>exactly ₹{amt:g}</b>, then press <b>I've Paid</b> and send your UTR.")
    await msg.answer_photo(make_qr(s["AUTO_UPI_ID"], amt), caption=cap, parse_mode="HTML",
                           reply_markup=KB([B("✅ I've Paid", "rc:paid")], [B("Cancel", "recharge")]))


@router.callback_query(F.data.in_({"rc:paid", "rc:retry"}))
async def ask_utr(cq: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("amount"):
        return await cq.answer("⌛ Session expired. Start the recharge again.", show_alert=True)
    await cq.answer()
    await state.set_state(RC.auto_utr)
    await _replace(cq, "🧾 <b>Send your 12-digit UTR</b> (or the FMP… transaction ID) of the payment you just made.",
                   KB([B("Cancel", "recharge")]))


def _not_found_kb():
    rows = [[B("🔄 Try Again", "rc:retry")], [B("I Already Paid", "rc:already")]]
    sup = normalize_support(SUPPORT_LINK)
    if sup:
        rows.append([B("Contact Support", url=sup)])
    rows.append([B("Back", "recharge")])
    return KB(*rows)


@router.message(StateFilter(RC.auto_utr), F.text, ~F.text.startswith("/"))
async def got_utr(msg: Message, state: FSMContext):
    data = await state.get_data()
    amt = data.get("amount")
    utr = payments.clean_id(msg.text)
    if not amt:
        await state.clear()
        return await msg.answer("⌛ Session expired. Start the recharge again.")
    if not (re.fullmatch(r"\d{12}", utr) or re.fullmatch(r"FMP[A-Z0-9]{6,40}", utr)):
        return await msg.answer("❌ Invalid. Send the 12-digit UTR (digits only) or the FMP… transaction ID.")
    if await payments.id_in_use([utr]):
        return await msg.answer("❌ <b>This UTR was already used.</b>", parse_mode="HTML",
                                reply_markup=KB([B("Back", "recharge")]))
    wait = await msg.answer("🔎 <i>Verifying your payment… this can take up to a minute.</i>", parse_mode="HTML")
    status, res = "notfound", None
    for i in range(VERIFY_ATTEMPTS):
        status, res = await payments.utr_lookup(utr, amt)
        if status == "found":
            break
        if i < VERIFY_ATTEMPTS - 1:
            await asyncio.sleep(VERIFY_GAP)
    if status == "found":
        r, bal = await payments.auto_upi_credit(msg.from_user.id, msg.from_user.username, msg.from_user.full_name, amt, utr, res)
        if r == "ok":
            await state.clear()
            return await edit(wait, f"✅ <b>Payment received!</b>\n{SEP}\n<b>Added:</b> {fmt_curr(amt)}\n<b>New balance:</b> {fmt_curr(bal)}",
                              KB([B("🏠 Home", "back_main")]))
        if r == "claimed":
            return await edit(wait, "❌ <b>This payment was already credited.</b>", KB([B("Back", "recharge")]))
        return await edit(wait, "⚠️ <b>Something went wrong while crediting.</b> Please contact support.", _not_found_kb())
    await state.update_data(utr=utr)
    await edit(wait, "❌ <b>Payment not found yet.</b>\n<i>Bank updates can take a minute. Try again, or if you have already paid "
                     "tap <b>I Already Paid</b> to send a screenshot for manual check.</i>", _not_found_kb())


@router.callback_query(F.data == "rc:already")
async def already_paid(cq: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("amount"):
        return await cq.answer("⌛ Session expired. Start the recharge again.", show_alert=True)
    await cq.answer()
    await state.set_state(RC.claim_shot)
    await _replace(cq, "📸 <b>Send a screenshot of your payment</b> (showing the UTR and amount).\n<i>An admin will verify it.</i>",
                   KB([B("Cancel", "recharge")]))


# =============================== MANUAL UPI ===============================
@router.callback_query(F.data == "rc:manual")
async def manual_start(cq: CallbackQuery, state: FSMContext):
    s = await get_settings()
    await cq.answer()
    cap = (f"💳 <b>Manual UPI Payment</b>\n{SEP}\n"
           + (f"<blockquote>Pay to UPI ID:\n<code>{esc(s['MANUAL_UPI_ID'])}</code></blockquote>\n" if s["MANUAL_UPI_ID"] else "")
           + "After paying, press <b>Deposit Done</b> and send the amount + screenshot.")
    kb = KB([B("✅ Deposit Done", "rc:mdone")], [B("Back", "recharge")])
    await _replace(cq, cap, kb, photo=s["MANUAL_QR_FILE_ID"] or None)


@router.callback_query(F.data == "rc:mdone")
async def manual_done(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    await state.set_state(RC.manual_amount)
    await _replace(cq, "💰 <b>Enter the amount you paid</b> (numbers only, e.g. 200)", KB([B("Cancel", "recharge")]))


@router.message(StateFilter(RC.manual_amount), F.text, ~F.text.startswith("/"))
async def manual_amount(msg: Message, state: FSMContext):
    amt = parse_amount(msg.text)
    if amt is None or amt > 1000000:
        return await msg.answer("❌ Enter a valid amount.")
    await state.update_data(amount=amt)
    await state.set_state(RC.manual_shot)
    await msg.answer(f"📸 <b>Now send the payment screenshot</b> for {fmt_curr(amt)}.", parse_mode="HTML")


# ===================== screenshot -> admin approval (both flows) =====================
async def _submit(msg: Message, state: FSMContext, method):
    data = await state.get_data()
    amt = data.get("amount")
    if not amt:
        await state.clear()
        return await msg.answer("⌛ Session expired. Start the recharge again.")
    photo = msg.photo[-1].file_id
    utr = payments.clean_id(data.get("utr"))
    res = await txns.insert_one({"user_id": msg.from_user.id, "username": msg.from_user.username,
                                 "full_name": msg.from_user.full_name, "amount": float(amt), "method": method,
                                 "utr": utr or None, "screenshot": photo, "status": "pending", "created_at": utcnow()})
    await state.clear()
    tid = str(res.inserted_id)
    cap = (f"💳 <b>New {'Manual' if method == 'manual_upi' else 'Auto-UPI claim'} payment</b>\n{SEP}\n"
           f"<b>User:</b> {esc(msg.from_user.full_name)} (<code>{msg.from_user.id}</code>)\n"
           f"<b>Amount:</b> {fmt_curr(amt)}\n" + (f"<b>UTR:</b> <code>{esc(utr)}</code>\n" if utr else ""))
    kb = KB([B("✅ Approve", f"rc:ok:{tid}"), B("❌ Decline", f"rc:no:{tid}")])
    sent = 0
    for a in ADMIN_IDS:
        try:
            await get_bot().send_photo(a, photo, caption=cap, parse_mode="HTML", reply_markup=kb)
            sent += 1
        except Exception:
            pass
    await msg.answer("✅ <b>Request submitted.</b>\nAn admin will verify your payment shortly. You will be notified.",
                     parse_mode="HTML", reply_markup=KB([B("🏠 Home", "back_main")]))


@router.message(StateFilter(RC.manual_shot), F.photo)
async def manual_shot(msg: Message, state: FSMContext):
    await _submit(msg, state, "manual_upi")


@router.message(StateFilter(RC.claim_shot), F.photo)
async def claim_shot(msg: Message, state: FSMContext):
    await _submit(msg, state, "auto_upi_claim")


@router.message(StateFilter(RC.manual_shot, RC.claim_shot), ~F.photo, ~F.text.startswith("/"))
async def need_photo(msg: Message):
    await msg.answer("📸 Please send the payment <b>screenshot as a photo</b>.", parse_mode="HTML")


@router.callback_query(F.data.startswith("rc:ok:") | F.data.startswith("rc:no:"))
async def decide(cq: CallbackQuery):
    if cq.from_user.id not in ADMIN_IDS:
        return await cq.answer("Not allowed.", show_alert=True)
    _, action, tid = cq.data.split(":", 2)
    bot = get_bot()
    if action == "ok":
        st, txn = await payments.approve_txn(tid, cq.from_user.id)
        if st == "ok":
            await cq.answer("Approved")
            try:
                await cq.message.edit_caption(caption=(cq.message.caption or "") + f"\n\n✅ <b>Approved</b> by {cq.from_user.id}",
                                              parse_mode="HTML", reply_markup=None)
            except Exception:
                pass
            u = await users.find_one({"_id": txn["user_id"]}) or {}
            try:
                await bot.send_message(txn["user_id"], f"✅ <b>Payment approved!</b>\n{fmt_curr(txn['amount'])} added. "
                                                       f"New balance: {fmt_curr(u.get('balance', 0))}", parse_mode="HTML")
            except Exception:
                pass
        elif st == "dup_utr":
            await cq.answer("❌ This UTR was already used - request declined.", show_alert=True)
            try:
                await cq.message.edit_caption(caption=(cq.message.caption or "") + "\n\n❌ <b>Declined (duplicate UTR)</b>",
                                              parse_mode="HTML", reply_markup=None)
            except Exception:
                pass
        else:
            await cq.answer("Already handled.", show_alert=True)
        return
    txn = await payments.decline_txn(tid, cq.from_user.id)
    if not txn:
        return await cq.answer("Already handled.", show_alert=True)
    await cq.answer("Declined")
    try:
        await cq.message.edit_caption(caption=(cq.message.caption or "") + f"\n\n❌ <b>Declined</b> by {cq.from_user.id}",
                                      parse_mode="HTML", reply_markup=None)
    except Exception:
        pass
    try:
        await bot.send_message(txn["user_id"], f"❌ <b>Your payment of {fmt_curr(txn['amount'])} was declined.</b>\n"
                                               "If you think this is a mistake, contact support.", parse_mode="HTML")
    except Exception:
        pass
