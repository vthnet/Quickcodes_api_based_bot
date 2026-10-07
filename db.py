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


import copy
import time
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from config import DATABASE_URL, DB_NAME
import notify

_client = AsyncIOMotorClient(DATABASE_URL)
db = _client[DB_NAME]

users = db["users"]
orders = db["orders"]            # history of everything a user bought
txns = db["transactions"]        # recharge requests
used_utrs = db["used_utrs"]      # UTR / txn ids that can never be used again
tasks = db["s3_tasks"]           # running OTP orders (Server 3 + WhatsApp)
smm_orders = db["smm_orders"]
settings_col = db["settings"]

DEFAULTS = {
    "services": {"tg": True, "wa": True, "otp": True, "smm": True},
    "api_keys": {"s2": "", "s3": "", "smm": ""},
    "profit": {"s2": 0.0, "s3": 0.0, "smm": 0.0},          # your profit % on top of Quick Codes prices
    "auto_upi_active": True,
    "manual_upi_active": True,
    "AUTO_UPI_ID": "",
    "UTR_API_URL": "https://subdict.qzz.io/check",
    "UTR_API_MAIL": "",
    "UTR_API_PASS": "",
    "MANUAL_UPI_ID": "",
    "MANUAL_QR_FILE_ID": None,
}

_cache = {"t": 0.0, "v": None}


def utcnow():
    return datetime.utcnow()


async def init_indexes():
    await tasks.create_index("order_id", unique=True)
    await tasks.create_index("status")
    await smm_orders.create_index([("user_id", 1), ("order_id", 1)])
    await orders.create_index([("user_id", 1), ("date", -1)])
    await txns.create_index("status")


async def get_settings(force=False):
    if not force and _cache["v"] is not None and time.time() - _cache["t"] < 3:
        return _cache["v"]
    doc = await settings_col.find_one({"_id": "bot_settings"})
    if not doc:
        doc = {"_id": "bot_settings", **copy.deepcopy(DEFAULTS)}
        await settings_col.insert_one(dict(doc))
    else:
        patch = {}
        for k, v in DEFAULTS.items():
            if k not in doc:
                patch[k] = copy.deepcopy(v)
            elif isinstance(v, dict):
                for kk, vv in v.items():
                    if kk not in doc[k]:
                        patch[f"{k}.{kk}"] = vv
        if patch:
            await settings_col.update_one({"_id": "bot_settings"}, {"$set": patch})
            doc = await settings_col.find_one({"_id": "bot_settings"})
    _cache.update(t=time.time(), v=doc)
    return doc


async def set_setting(**kv):
    """set_setting(**{"api_keys.s2": "qc_s2_..."})"""
    await settings_col.update_one({"_id": "bot_settings"}, {"$set": kv}, upsert=True)
    _cache["v"] = None


async def service_on(key):
    return bool((await get_settings())["services"].get(key, True))


async def profit_pct(server):
    return float((await get_settings())["profit"].get(server, 0.0) or 0.0)


# ---------- wallet (atomic) ----------
async def get_balance(uid):
    u = await users.find_one({"_id": uid}, {"balance": 1}) or {}
    return round(float(u.get("balance", 0.0)), 2)


async def charge(uid, amount):
    amount = round(float(amount), 2)
    r = await users.update_one({"_id": uid, "balance": {"$gte": amount}}, {"$inc": {"balance": -amount}})
    return r.modified_count == 1


async def refund(uid, amount):
    amount = round(float(amount), 2)
    try:
        await users.update_one({"_id": uid}, {"$inc": {"balance": amount}})
        return True
    except Exception:
        print(f"[wallet] !!! REFUND FAILED user={uid} amount={amount}")
        await notify.alert_admins(f"🚨 <b>REFUND FAILED</b> user <code>{uid}</code> amount ₹{amount:g} - credit manually with /credit")
        return False
