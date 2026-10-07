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

"""Recharge logic: Auto UPI (UTR verification API), manual approval, single-use UTR protection."""
import re
import aiohttp
from bson import ObjectId
from pymongo.errors import DuplicateKeyError
from db import users, txns, used_utrs, get_settings, utcnow

MIN_AUTO_UPI = 5
MAX_AUTO_UPI = 100000
VERIFY_ATTEMPTS = 3
VERIFY_GAP = 4


def clean_id(v):
    v = re.sub(r"\s+", "", str(v or "")).upper()
    return "" if v in ("NONE", "NULL") else v


async def id_in_use(ids):
    ids = [i for i in ids if i]
    if not ids:
        return False
    if await used_utrs.find_one({"_id": {"$in": ids}}):
        return True
    return await txns.find_one({"status": "approved", "$or": [{"utr": {"$in": ids}}, {"transaction_id": {"$in": ids}}]}) is not None


async def claim_ids(ids, meta):
    """Atomically block UTR / Txn IDs. False (and nothing blocked) if any is already blocked."""
    done = []
    for i in dict.fromkeys(x for x in ids if x):
        try:
            await used_utrs.insert_one({"_id": i, **meta, "at": utcnow()})
            done.append(i)
        except DuplicateKeyError:
            if done:
                await used_utrs.delete_many({"_id": {"$in": done}})
            return False
    return True


async def utr_lookup(utr, amount):
    """-> ('found', json) | ('notfound', json) | ('error', None)"""
    s = await get_settings()
    params = {"mail": s.get("UTR_API_MAIL", ""), "apppass": s.get("UTR_API_PASS", ""), "amount": amount}
    params["txnid" if utr.startswith("FMP") else "utr"] = utr
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=25)) as sess:
            async with sess.get(s.get("UTR_API_URL") or "https://subdict.qzz.io/check", params=params) as resp:
                res = await resp.json(content_type=None)
    except Exception as e:
        print(f"[UTR API] error: {e!r}")
        return "error", None
    if not isinstance(res, dict):
        return "error", None
    if str(res.get("status", "")).lower() == "found" or str(res.get("result", "")).lower() == "found":
        return "found", res
    return "notfound", res


async def auto_upi_credit(uid, username, full_name, amount, utr, res):
    """Payment was found by the API -> credit once. -> ('ok', new_balance) | ('claimed', None) | ('error', None)"""
    found_utr = clean_id(res.get("utr"))
    found_txn = clean_id(res.get("transaction_id"))
    ids = [utr, found_utr, found_txn]
    if await id_in_use([found_utr, found_txn]) or not await claim_ids(ids, {"user_id": uid, "source": "auto_upi"}):
        return "claimed", None
    amt = float(amount)
    try:
        await txns.insert_one({"user_id": uid, "username": username, "full_name": full_name, "amount": amt,
                               "method": "auto_upi", "utr": found_utr or utr, "transaction_id": found_txn,
                               "status": "approved", "created_at": utcnow()})
        await users.update_one({"_id": uid}, {"$inc": {"balance": amt}})
    except Exception as e:
        print(f"[auto upi] credit error: {e!r}")
        await used_utrs.delete_many({"_id": {"$in": [i for i in ids if i]}})
        return "error", None
    u = await users.find_one({"_id": uid}) or {}
    return "ok", float(u.get("balance", amt))


async def approve_txn(oid_str, admin_id):
    """-> (status, txn)  status: ok | invalid | done | dup_utr"""
    try:
        oid = ObjectId(oid_str)
    except Exception:
        return "invalid", None
    txn = await txns.find_one_and_update({"_id": oid, "status": "pending"},
                                         {"$set": {"status": "approved", "approved_by": admin_id}})
    if not txn:
        return "done", None
    utr = clean_id(txn.get("utr"))
    if utr and not await claim_ids([utr], {"user_id": txn["user_id"], "source": "admin_approved", "txn": str(oid)}):
        await txns.update_one({"_id": oid}, {"$set": {"status": "declined", "decline_reason": "duplicate_utr"}})
        return "dup_utr", txn
    await users.update_one({"_id": txn["user_id"]}, {"$inc": {"balance": txn["amount"]}})
    return "ok", txn


async def decline_txn(oid_str, admin_id):
    try:
        oid = ObjectId(oid_str)
    except Exception:
        return None
    return await txns.find_one_and_update({"_id": oid, "status": "pending"},
                                          {"$set": {"status": "declined", "declined_by": admin_id}})
