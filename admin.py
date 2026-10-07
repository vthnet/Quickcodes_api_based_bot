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




"""/admin panel: services ON/OFF, profit %, API keys, live balances, payment settings, manual credit/debit."""
import re
from aiogram import Router, F
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from config import ADMIN_IDS, BOT_TITLE
from db import get_settings, set_setting, users
from flows import admin_credit, admin_debit
from qc import qc
from utils import B, KB, esc, fmt_curr, edit, SEP

router = Router()
IS_ADMIN = F.from_user.id.in_(ADMIN_IDS)

SERVICES = [("tg", "Telegram Accounts"), ("wa", "WhatsApp Accounts"), ("otp", "All Apps OTP"), ("smm", "SMM Panel")]
APIS = [("s2", "Server 2", "Telegram accounts"), ("s3", "Server 3", "OTP + WhatsApp"), ("smm", "SMM Panel", "social media")]
PAY_FIELDS = {
    "AUTO_UPI_ID": ("Auto UPI ID", "Send the UPI ID that receives Auto UPI payments (e.g. name@bank)."),
    "UTR_API_URL": ("UTR API URL", "Send the UTR verification API URL (https://…)."),
    "UTR_API_MAIL": ("UTR API Mail", "Send the e-mail used by the UTR verification API."),
    "UTR_API_PASS": ("UTR App Password", "Send the app password for that e-mail."),
    "MANUAL_UPI_ID": ("Manual UPI ID", "Send the UPI ID for manual payments (e.g. name@bank)."),
    "MANUAL_QR_FILE_ID": ("Manual QR", "Send the QR code as a PHOTO."),
}
SECRET = {"UTR_API_PASS"}


class Adm(StatesGroup):
    key = State()
    profit = State()
    value = State()
    credit = State()
    debit = State()


def mask(v, keep=6):
    v = v or ""
    return "❌ not set" if not v else (v[:keep] + "…" + v[-4:] if len(v) > keep + 6 else "••••")


async def _del(msg):
    try:
        await msg.delete()
    except Exception:
        pass


# ============================== home ==============================
async def home(target):
    text = f"⚙️ <b>ADMIN PANEL</b>\n{SEP}\n<i>{esc(BOT_TITLE)}</i>"
    kb = KB([B("🛎 Services ON/OFF", "adm:svc"), B("📈 Profit %", "adm:profit")],
            [B("🔑 API Keys", "adm:api"), B("💰 Live Balances", "adm:bal")],
            [B("💳 Payments", "adm:pay")])
    await edit(target, text, kb)


@router.message(Command("admin"), IS_ADMIN)
async def admin_cmd(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer(f"⚙️ <b>ADMIN PANEL</b>\n{SEP}\n<i>{esc(BOT_TITLE)}</i>", parse_mode="HTML",
                     reply_markup=KB([B("🛎 Services ON/OFF", "adm:svc"), B("📈 Profit %", "adm:profit")],
                                     [B("🔑 API Keys", "adm:api"), B("💰 Live Balances", "adm:bal")],
                                     [B("💳 Payments", "adm:pay")]))


@router.callback_query(F.data == "adm:home", IS_ADMIN)
async def home_cb(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    await cq.answer()
    await home(cq)


# ============================== services ==============================
async def render_services(cq):
    s = await get_settings()
    rows = [[B(f"{'✅' if s['services'].get(k, True) else '❌'} {n}", f"adm:tog:{k}")] for k, n in SERVICES]
    rows.append([B("⬅️ Back", "adm:home")])
    await edit(cq, f"🛎 <b>Services</b>\n{SEP}\n<i>Tap to switch a service ON / OFF for your users.</i>", KB(*rows))


@router.callback_query(F.data == "adm:svc", IS_ADMIN)
async def svc(cq: CallbackQuery):
    await cq.answer()
    await render_services(cq)


@router.callback_query(F.data.startswith("adm:tog:"), IS_ADMIN)
async def svc_toggle(cq: CallbackQuery):
    key = cq.data.split(":")[2]
    if key not in dict(SERVICES):
        return await cq.answer()
    s = await get_settings()
    new = not s["services"].get(key, True)
    await set_setting(**{f"services.{key}": new})
    await cq.answer(f"{dict(SERVICES)[key]}: {'ON' if new else 'OFF'}")
    await render_services(cq)


# ============================== profit % ==============================
async def render_profit(cq):
    s = await get_settings()
    lines = [f"• <b>{n}</b> ({d}): <b>{float(s['profit'].get(k, 0)):g}%</b>" for k, n, d in APIS]
    rows = [[B(f"✏️ {n} profit %", f"adm:pset:{k}")] for k, n, d in APIS]
    rows.append([B("⬅️ Back", "adm:home")])
    await edit(cq, f"📈 <b>Profit %</b>\n{SEP}\n" + "\n".join(lines) +
               "\n\n<i>Your price = Quick Codes price + this %. Server 3 % applies to OTP <b>and</b> WhatsApp.</i>", KB(*rows))


@router.callback_query(F.data == "adm:profit", IS_ADMIN)
async def profit(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    await cq.answer()
    await render_profit(cq)


@router.callback_query(F.data.startswith("adm:pset:"), IS_ADMIN)
async def profit_prompt(cq: CallbackQuery, state: FSMContext):
    k = cq.data.split(":")[2]
    if k not in {a[0] for a in APIS}:
        return await cq.answer()
    await cq.answer()
    await state.set_state(Adm.profit)
    await state.update_data(srv=k)
    n = next(a[1] for a in APIS if a[0] == k)
    await edit(cq, f"✏️ <b>{n} profit %</b>\nSend a number from 0 to 1000 (example: <code>15</code> or <code>12.5</code>).",
               KB([B("⬅️ Back", "adm:profit")]))


@router.message(StateFilter(Adm.profit), IS_ADMIN, F.text, ~F.text.startswith("/"))
async def profit_save(msg: Message, state: FSMContext):
    try:
        v = float(msg.text.strip().replace("%", ""))
        assert 0 <= v <= 1000
    except Exception:
        return await msg.answer("❌ Send a number between 0 and 1000.")
    k = (await state.get_data()).get("srv")
    await state.clear()
    await set_setting(**{f"profit.{k}": round(v, 2)})
    await msg.answer(f"✅ Profit for <b>{next(a[1] for a in APIS if a[0] == k)}</b> set to <b>{v:g}%</b>.", parse_mode="HTML",
                     reply_markup=KB([B("📈 Profit %", "adm:profit")]))


# ============================== API keys ==============================
async def render_api(cq):
    s = await get_settings()
    lines = [f"• <b>{n}</b> ({d})\n   <code>{esc(mask(s['api_keys'].get(k)))}</code>" for k, n, d in APIS]
    rows = [[B(f"✏️ Change {n} key", f"adm:kset:{k}")] for k, n, d in APIS]
    rows.append([B("⬅️ Back", "adm:home")])
    await edit(cq, f"🔑 <b>Quick Codes API Keys</b>\n{SEP}\n" + "\n".join(lines) +
               "\n\n<i>Get the keys in the Quick Codes bot → 🔑 API Keys.</i>", KB(*rows))


@router.callback_query(F.data == "adm:api", IS_ADMIN)
async def api(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    await cq.answer()
    await render_api(cq)


@router.callback_query(F.data.startswith("adm:kset:"), IS_ADMIN)
async def key_prompt(cq: CallbackQuery, state: FSMContext):
    k = cq.data.split(":")[2]
    if k not in {a[0] for a in APIS}:
        return await cq.answer()
    await cq.answer()
    await state.set_state(Adm.key)
    await state.update_data(srv=k)
    n = next(a[1] for a in APIS if a[0] == k)
    await edit(cq, f"✏️ <b>Send your {n} API key</b>\nIt starts with <code>qc_{k}_</code>.\n"
                   "<i>Your message will be deleted right after for safety.</i>", KB([B("⬅️ Back", "adm:api")]))


@router.message(StateFilter(Adm.key), IS_ADMIN, F.text, ~F.text.startswith("/"))
async def key_save(msg: Message, state: FSMContext):
    k = (await state.get_data()).get("srv")
    key = msg.text.strip()
    await _del(msg)
    name = next(a[1] for a in APIS if a[0] == k)
    if not key.startswith(f"qc_{k}_"):
        return await msg.answer(f"❌ That is not a {name} key. It must start with <code>qc_{k}_</code>. Send it again.", parse_mode="HTML")
    st, d = await qc(k, "GET", "/v1/balance", key=key)
    if st in (401, 403):
        return await msg.answer(f"❌ <b>Key rejected:</b> {esc(d.get('message'))}\nSend a valid key.", parse_mode="HTML")
    await state.clear()
    await set_setting(**{f"api_keys.{k}": key})
    note = (f"💰 Quick Codes wallet: <b>{fmt_curr(d.get('balance'))}</b>" if d.get("ok")
            else f"⚠️ Saved, but the API could not be checked right now ({esc(d.get('message'))}).")
    await msg.answer(f"✅ <b>{name} key saved.</b>\n{note}", parse_mode="HTML", reply_markup=KB([B("🔑 API Keys", "adm:api")]))


# ============================== live balances ==============================
@router.callback_query(F.data == "adm:bal", IS_ADMIN)
async def balances(cq: CallbackQuery):
    await cq.answer("Checking…")
    lines = []
    for k, n, d in APIS:
        st, r = await qc(k, "GET", "/v1/balance")
        if r.get("ok"):
            lines.append(f"✅ <b>{n}</b> — Quick Codes wallet: <b>{fmt_curr(r.get('balance'))}</b>")
        elif r.get("error") == "no_key":
            lines.append(f"➖ <b>{n}</b> — key not set")
        else:
            lines.append(f"❌ <b>{n}</b> — {esc(r.get('message') or r.get('error'))}")
    await edit(cq, f"💰 <b>Live API Balances</b>\n{SEP}\n" + "\n".join(lines) +
               "\n\n<i>This is your Quick Codes wallet. Recharge it in the Quick Codes bot when it runs low.</i>",
               KB([B("🔄 Refresh", "adm:bal")], [B("⬅️ Back", "adm:home")]))


# ============================== payments ==============================
async def render_pay(cq):
    s = await get_settings()
    qr = "✅ set" if s["MANUAL_QR_FILE_ID"] else "❌ not set"
    text = (f"💳 <b>Payments</b>\n{SEP}\n"
            f"<b>Auto UPI:</b> {'🟢 ON' if s['auto_upi_active'] else '🔴 OFF'}\n"
            f"• UPI ID: <code>{esc(s['AUTO_UPI_ID'] or '-')}</code>\n"
            f"• API URL: <code>{esc(s['UTR_API_URL'] or '-')}</code>\n"
            f"• Mail: <code>{esc(s['UTR_API_MAIL'] or '-')}</code>\n"
            f"• App password: {'✅ set' if s['UTR_API_PASS'] else '❌ not set'}\n\n"
            f"<b>Manual UPI:</b> {'🟢 ON' if s['manual_upi_active'] else '🔴 OFF'}\n"
            f"• UPI ID: <code>{esc(s['MANUAL_UPI_ID'] or '-')}</code>\n• QR: {qr}")
    kb = KB([B(f"Auto UPI: {'ON' if s['auto_upi_active'] else 'OFF'}", "adm:ptog:auto_upi_active"),
             B(f"Manual UPI: {'ON' if s['manual_upi_active'] else 'OFF'}", "adm:ptog:manual_upi_active")],
            [B("Auto UPI ID", "adm:fset:AUTO_UPI_ID"), B("UTR API URL", "adm:fset:UTR_API_URL")],
            [B("UTR Mail", "adm:fset:UTR_API_MAIL"), B("UTR App Pass", "adm:fset:UTR_API_PASS")],
            [B("Manual UPI ID", "adm:fset:MANUAL_UPI_ID"), B("Manual QR", "adm:fset:MANUAL_QR_FILE_ID")],
            [B("⬅️ Back", "adm:home")])
    await edit(cq, text, kb)


@router.callback_query(F.data == "adm:pay", IS_ADMIN)
async def pay(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    await cq.answer()
    await render_pay(cq)


@router.callback_query(F.data.startswith("adm:ptog:"), IS_ADMIN)
async def pay_toggle(cq: CallbackQuery):
    k = cq.data.split(":")[2]
    if k not in ("auto_upi_active", "manual_upi_active"):
        return await cq.answer()
    s = await get_settings()
    await set_setting(**{k: not s[k]})
    await cq.answer("Updated")
    await render_pay(cq)


@router.callback_query(F.data.startswith("adm:fset:"), IS_ADMIN)
async def field_prompt(cq: CallbackQuery, state: FSMContext):
    f = cq.data.split(":")[2]
    if f not in PAY_FIELDS:
        return await cq.answer()
    await cq.answer()
    await state.set_state(Adm.value)
    await state.update_data(field=f)
    await edit(cq, f"✏️ <b>{PAY_FIELDS[f][0]}</b>\n{PAY_FIELDS[f][1]}", KB([B("⬅️ Back", "adm:pay")]))


@router.message(StateFilter(Adm.value), IS_ADMIN, F.photo)
async def field_photo(msg: Message, state: FSMContext):
    f = (await state.get_data()).get("field")
    if f != "MANUAL_QR_FILE_ID":
        return await msg.answer("❌ Send text for this field.")
    await state.clear()
    await set_setting(MANUAL_QR_FILE_ID=msg.photo[-1].file_id)
    await msg.answer("✅ Manual QR saved.", reply_markup=KB([B("💳 Payments", "adm:pay")]))


@router.message(StateFilter(Adm.value), IS_ADMIN, F.text, ~F.text.startswith("/"))
async def field_text(msg: Message, state: FSMContext):
    f = (await state.get_data()).get("field")
    v = msg.text.strip()
    if f in SECRET:
        await _del(msg)
    if f == "MANUAL_QR_FILE_ID":
        return await msg.answer("📸 Please send the QR as a photo.")
    if f in ("AUTO_UPI_ID", "MANUAL_UPI_ID", "UTR_API_MAIL") and "@" not in v:
        return await msg.answer("❌ That does not look right (missing @). Send it again.")
    if f == "UTR_API_URL" and not v.startswith(("http://", "https://")):
        return await msg.answer("❌ The URL must start with http:// or https://")
    await state.clear()
    await set_setting(**{f: v})
    await msg.answer(f"✅ <b>{PAY_FIELDS[f][0]}</b> saved.", parse_mode="HTML", reply_markup=KB([B("💳 Payments", "adm:pay")]))


# ============================== manual credit / debit ==============================
def _parse(text):
    m = re.match(r"^\s*(\d{1,15})[\s,]+(\d+(?:\.\d+)?)\s*$", text or "")
    return (int(m.group(1)), float(m.group(2))) if m else None


async def _apply(msg, text, credit):
    p = _parse(text)
    if not p or p[1] <= 0:
        return await msg.answer("❌ Format: <code>user_id amount</code>  (example: <code>123456789 50</code>)", parse_mode="HTML")
    uid, amt = p
    u = await users.find_one({"_id": uid})
    if not u:
        return await msg.answer("❌ User not found (they must have started the bot).")
    await (admin_credit if credit else admin_debit)(uid, amt)
    nb = (await users.find_one({"_id": uid}) or {}).get("balance", 0)
    await msg.answer(f"✅ {'Credited' if credit else 'Debited'} {fmt_curr(amt)} {'to' if credit else 'from'} <code>{uid}</code>\n"
                     f"New balance: <b>{fmt_curr(nb)}</b>", parse_mode="HTML")


@router.message(Command("credit"), IS_ADMIN)
async def credit_cmd(msg: Message, command: CommandObject, state: FSMContext):
    await state.clear()
    if command.args:
        return await _apply(msg, command.args, True)
    await state.set_state(Adm.credit)
    await msg.answer("➕ <b>Add balance</b>\nSend: <code>user_id amount</code>", parse_mode="HTML")


@router.message(Command("debit"), IS_ADMIN)
async def debit_cmd(msg: Message, command: CommandObject, state: FSMContext):
    await state.clear()
    if command.args:
        return await _apply(msg, command.args, False)
    await state.set_state(Adm.debit)
    await msg.answer("➖ <b>Deduct balance</b>\nSend: <code>user_id amount</code>", parse_mode="HTML")


@router.message(StateFilter(Adm.credit), IS_ADMIN, F.text, ~F.text.startswith("/"))
async def credit_state(msg: Message, state: FSMContext):
    await state.clear()
    await _apply(msg, msg.text, True)


@router.message(StateFilter(Adm.debit), IS_ADMIN, F.text, ~F.text.startswith("/"))
async def debit_state(msg: Message, state: FSMContext):
    await state.clear()
    await _apply(msg, msg.text, False)
