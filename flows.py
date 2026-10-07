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


"""All money-moving logic (no Telegram code here, so it can be tested on its own)."""
import time
from db import (orders, tasks, smm_orders, users, profit_pct, charge, refund, get_balance, utcnow)
from qc import qc, explain, BUSY_USER
import notify

OTP_TIMEOUT = 300      # seconds - API cancels + refunds after this
CANCEL_LOCK = 180      # user may cancel only after this many seconds without OTP


def with_profit(price, pct, whole=False):
    price = float(price or 0)
    if not pct:
        return round(price, 2)
    v = price * (1 + float(pct) / 100.0)
    return float(int(v) if v == int(v) else int(v) + 1) if whole else round(v + 1e-9, 2)


async def _record(order):
    try:
        await orders.insert_one(dict(order))
    except Exception as e:
        print(f"[orders] could not save history: {e!r}")


async def _ambiguous(server_name, uid, what, d):
    await notify.alert_admins(
        f"⚠️ <b>{server_name}: no answer while buying</b> ({what}) for user <code>{uid}</code>.\n"
        "User was refunded. If the Quick Codes API actually completed it, check your Quick Codes orders / wallet.",
        key=f"amb:{uid}:{what}", every=60)


# =====================================================================
#                           SERVER 2  (Telegram accounts)
# =====================================================================
_s2 = {"t": 0.0, "rows": None}


async def s2_rows(force=False):
    now = time.time()
    if not force and _s2["rows"] is not None and now - _s2["t"] < 15:
        return _s2["rows"]
    st, d = await qc("s2", "GET", "/v1/s2/countries")
    if d.get("ok"):
        _s2.update(t=now, rows=d.get("countries") or [])
        return _s2["rows"]
    await explain("s2", st, d)
    if _s2["rows"] is not None and now - _s2["t"] < 300:
        return _s2["rows"]
    return None


async def s2_view(force=False):
    rows = await s2_rows(force)
    if rows is None:
        return None
    pct = await profit_pct("s2")
    return [{**r, "my_price": with_profit(r["price"], pct)} for r in rows]


async def buy_tg(uid, code, shown):
    rows = await s2_view(force=True)
    if rows is None:
        return {"kind": "fail", "text": BUSY_USER}
    row = next((r for r in rows if r["country_code"] == code), None)
    if not row:
        return {"kind": "fail", "text": "❌ Country no longer available"}
    if int(row.get("stock", 0)) <= 0:
        return {"kind": "stock", "text": "⚠️ <b>Out of Stock!</b>"}
    price = row["my_price"]
    if price > float(shown) + 0.009:
        return {"kind": "price", "price": price}
    if not await charge(uid, price):
        return {"kind": "funds", "need": round(price - await get_balance(uid), 2)}

    st, d = await qc("s2", "POST", "/v1/s2/buy", json={"country_code": code}, timeout=60)
    if not d.get("ok"):
        await refund(uid, price)
        if d.get("error") == "timeout":
            await _ambiguous("Server 2", uid, f"Telegram {code}", d)
        kind, text = await explain("s2", st, d)
        return {"kind": kind, "text": text}

    country = d.get("country") or row.get("name") or code
    order = {"user_id": uid, "type": "tg", "title": f"Telegram · {country}", "number": d["number"],
             "price": price, "api_price": d.get("price"), "api_order_id": d["order_id"], "date": utcnow()}
    await _record(order)
    return {"kind": "ok", "order": order, "country": country, "balance": await get_balance(uid)}


async def tg_code(uid, api_order_id):
    o = await orders.find_one({"user_id": uid, "type": "tg", "api_order_id": api_order_id})
    if not o:
        return {"kind": "missing"}
    if o.get("code"):
        return {"kind": "ok", "number": o["number"], "code": o["code"], "password": o.get("password")}
    st, d = await qc("s2", "GET", f"/v1/s2/code/{api_order_id}")
    if d.get("ok") and d.get("code"):
        await orders.update_one({"_id": o["_id"]}, {"$set": {"code": d["code"], "password": d.get("password")}})
        return {"kind": "ok", "number": o["number"], "code": d["code"], "password": d.get("password")}
    if d.get("ok"):
        return {"kind": "wait"}
    kind, text = await explain("s2", st, d)
    return {"kind": "fail", "text": text}


# =====================================================================
#                SERVER 3  (all apps OTP + WhatsApp accounts)
# =====================================================================
_cat3 = {"t": 0.0, "v": None}
_cty3 = {}
_off3 = {}


async def s3_catalog():
    now = time.time()
    if _cat3["v"] and now - _cat3["t"] < 600:
        return _cat3["v"]
    items, offset = {}, 0
    while True:
        st, d = await qc("s3", "GET", "/v1/s3/services", params={"limit": 200, "offset": offset})
        if not d.get("ok"):
            await explain("s3", st, d)
            break
        for s in d.get("services") or []:
            items[str(s["service"])] = {"name": s["name"]}
        offset += 200
        if not d.get("services") or offset >= int(d.get("total", 0)):
            break
    if items:
        _cat3.update(t=now, v=items)
        return items
    return _cat3["v"]          # stale copy or None


def norm(s):
    return " ".join(str(s or "").lower().replace("-", " ").split())


def find_service(cat, wanted):
    t = norm(wanted)
    for sid, e in cat.items():
        if norm(e["name"]) == t:
            return sid
    for sid, e in cat.items():
        if t in norm(e["name"]):
            return sid
    return None


def is_wa(name):
    return norm(name) == "whatsapp"


def search_services(cat, q, limit=16):
    q = norm(q)
    hits = [(sid, e) for sid, e in cat.items() if q in norm(e["name"])]
    hits.sort(key=lambda kv: (not norm(kv[1]["name"]).startswith(q), norm(kv[1]["name"])))
    return hits[:limit]


async def s3_countries(sid, full=False, force=False):
    key = (sid, bool(full))
    now = time.time()
    c = _cty3.get(key)
    if not force and c and now - c["t"] < 60:
        rows = c["rows"]
    else:
        st, d = await qc("s3", "GET", "/v1/s3/countries", params={"service": sid, "full": int(bool(full))}, timeout=45)
        if not d.get("ok"):
            await explain("s3", st, d)
            if c:
                rows = c["rows"]
            else:
                return None
        else:
            rows = d.get("countries") or []
            _cty3[key] = {"t": now, "rows": rows}
    pct = await profit_pct("s3")
    out = [{**r, "my_price": with_profit(r["min_price"], pct, whole=True)} for r in rows if int(r.get("stock", 0)) > 0]
    return out


def drop_s3_cache(sid=None):
    for k in [k for k in _cty3 if sid is None or k[0] == sid]:
        _cty3.pop(k, None)
    for k in [k for k in _off3 if sid is None or k[0] == sid]:
        _off3.pop(k, None)


async def s3_offers(sid, cid, force=False):
    key = (sid, str(cid))
    now = time.time()
    c = _off3.get(key)
    if not force and c and now - c["t"] < 20:
        data = c
    else:
        st, d = await qc("s3", "GET", "/v1/s3/offers", params={"service": sid, "country": cid}, timeout=45)
        if not d.get("ok"):
            await explain("s3", st, d)
            if not c:
                return None
            data = c
        else:
            data = {"t": now, "name": d.get("country_name") or f"Country {cid}", "ops": d.get("operators") or []}
            _off3[key] = data
    pct = await profit_pct("s3")
    ops = [{**o, "my_price": with_profit(o["price"], pct, whole=True)} for o in data["ops"] if int(o.get("stock", 0)) > 0]
    ops.sort(key=lambda o: o["my_price"])
    return data["name"], ops


async def buy_s3(uid, sid, cid, op, shown, chat_id, msg_id):
    cat = await s3_catalog()
    if not cat or sid not in cat:
        return {"kind": "fail", "text": BUSY_USER}
    off = await s3_offers(sid, cid, force=True)
    if off is None:
        return {"kind": "fail", "text": BUSY_USER}
    _, ops = off
    row = next((o for o in ops if str(o["operator"]) == str(op)), None)
    if not row:
        return {"kind": "stock", "text": f"❌ Operator {op} has no numbers right now."}
    price = row["my_price"]
    if price > float(shown) + 0.009:
        return {"kind": "price", "price": price}
    if not await charge(uid, price):
        return {"kind": "funds", "need": round(price - await get_balance(uid), 2)}

    st, d = await qc("s3", "POST", "/v1/s3/buy", json={"service": sid, "country": str(cid), "operator": str(op)}, timeout=60)
    if not d.get("ok"):
        await refund(uid, price)
        if d.get("error") == "timeout":
            await _ambiguous("Server 3", uid, f"{cat[sid]['name']} / {cid} / op {op}", d)
        kind, text = await explain("s3", st, d)
        return {"kind": kind, "text": text}

    task = {"order_id": d["order_id"], "user_id": uid, "chat_id": chat_id, "msg_id": msg_id,
            "phone": str(d["number"]), "price": price, "api_price": d.get("price"), "sid": sid,
            "service": d.get("service") or cat[sid]["name"], "country_id": str(cid),
            "country": d.get("country") or "", "operator": str(op), "ts": time.time(),
            "status": "active", "last_edit": 0.0}
    try:
        await tasks.insert_one(dict(task))
    except Exception as e:
        print(f"[s3] could not save task: {e!r}")
        await refund(uid, price)
        await notify.alert_admins(f"🚨 <b>Server 3: order {d['order_id']} bought but NOT saved</b> (user <code>{uid}</code>). "
                                  "User refunded; the API will time it out and refund your Quick Codes wallet.")
        return {"kind": "fail", "text": BUSY_USER}
    return {"kind": "ok", "task": task, "balance": await get_balance(uid)}


async def close_task(order_id, new_status, **extra):
    """atomic active -> new_status. Only the winner gets the doc (prevents double delivery / double refund)."""
    return await tasks.find_one_and_update({"order_id": order_id, "status": "active"},
                                           {"$set": {"status": new_status, **extra}})


async def s3_poll(t):
    st, d = await qc("s3", "GET", f"/v1/s3/status/{t['order_id']}")
    if d.get("ok"):
        s = d.get("status")
        if s == "completed":
            won = await close_task(t["order_id"], "completed", otp=d.get("otp"))
            if won:
                await _record({"user_id": t["user_id"], "type": "wa" if is_wa(t["service"]) else "otp",
                               "title": f"{t['service']} · {t['country']}", "number": t["phone"], "price": t["price"],
                               "otp": d.get("otp"), "date": utcnow()})
            return {"act": "completed", "won": bool(won), "otp": d.get("otp")}
        if s == "cancelled":
            won = await close_task(t["order_id"], "cancelled")
            if won:
                await refund(t["user_id"], t["price"])
            return {"act": "cancelled", "won": bool(won)}
        return {"act": "active", "left": int(d.get("expires_in") or 0)}
    lost = d.get("error") == "order_not_found"
    if lost or time.time() - t["ts"] > OTP_TIMEOUT + 300:
        won = await close_task(t["order_id"], "cancelled", cancel_reason="lost")
        if won:
            await refund(t["user_id"], t["price"])
            await notify.alert_admins(f"⚠️ Server 3 order <code>{t['order_id']}</code> could not be tracked - "
                                      f"user <code>{t['user_id']}</code> was refunded ₹{t['price']:g}.")
        return {"act": "cancelled", "won": bool(won)}
    return {"act": "error"}


async def s3_cancel(uid, order_id):
    t = await tasks.find_one({"order_id": order_id, "user_id": uid, "status": "active"})
    if not t:
        return {"kind": "gone"}
    elapsed = time.time() - t["ts"]
    if elapsed < CANCEL_LOCK:
        return {"kind": "locked", "left": int(CANCEL_LOCK - elapsed)}
    st, d = await qc("s3", "POST", f"/v1/s3/cancel/{order_id}")
    if d.get("ok") and d.get("status") == "cancelled":
        won = await close_task(order_id, "cancelled", cancel_reason="user")
        if won:
            await refund(uid, t["price"])
        return {"kind": "cancelled", "task": t, "won": bool(won)}
    if d.get("ok") and d.get("status") == "completed":
        r = await s3_poll(t)
        return {"kind": "completed", "task": t, "otp": d.get("otp"), "won": r.get("won")}
    if d.get("error") == "cancel_locked":
        return {"kind": "locked", "left": int(d.get("retry_after") or 15)}
    kind, text = await explain("s3", st, d)
    return {"kind": "fail", "text": text}


# =====================================================================
#                              SMM PANEL
# =====================================================================
_smm = {"t": 0.0, "v": None}


def needs_comments(s):
    return "comments" in str(s.get("type", "")).lower()


def is_package(s):
    return s.get("rate_unit") == "package"


async def smm_catalog():
    now = time.time()
    if _smm["v"] and now - _smm["t"] < 600:
        return _smm["v"]
    rows, offset = [], 0
    while True:
        st, d = await qc("smm", "GET", "/v1/smm/services", params={"limit": 500, "offset": offset}, timeout=60)
        if not d.get("ok"):
            await explain("smm", st, d)
            break
        rows += d.get("services") or []
        offset += 500
        if not d.get("services") or offset >= int(d.get("total", 0)):
            break
    if not rows:
        return _smm["v"]
    services = {str(s["service"]): s for s in rows}
    apps = {}
    for s in rows:
        apps.setdefault(s.get("app") or "others", {}).setdefault(s["category"], []).append(s)
    byapp = {}
    for slug, cats in apps.items():
        byapp[slug] = [(cn, sorted(v, key=lambda x: x["rate"])) for cn, v in sorted(cats.items())]
    cat = {"services": services, "apps": byapp}
    _smm.update(t=now, v=cat)
    return cat


def smm_cost(srv, qty, pct):
    rate = with_profit(srv["rate"], pct)
    if is_package(srv):
        return round(rate, 2)
    return max(round(rate * qty / 1000.0, 2), 0.01)


async def buy_smm(uid, sid, link, qty, comments, shown):
    cat = await smm_catalog()
    srv = (cat or {}).get("services", {}).get(str(sid))
    if not srv:
        return {"kind": "fail", "text": "❌ This service is no longer available."}
    pct = await profit_pct("smm")
    cost = smm_cost(srv, qty, pct)
    if cost > float(shown) + 0.009:
        return {"kind": "price", "price": cost}
    if not await charge(uid, cost):
        return {"kind": "funds", "need": round(cost - await get_balance(uid), 2)}

    body = {"service": str(sid), "link": link}
    if needs_comments(srv):
        body["comments"] = comments
    elif not is_package(srv):
        body["quantity"] = int(qty)
    st, d = await qc("smm", "POST", "/v1/smm/order", json=body, timeout=70)

    base = {"user_id": uid, "service_id": str(sid), "service": srv["name"], "link": link, "qty": qty, "cost": cost,
            "refunded": False, "refund_amount": 0.0, "can_refill": bool(srv.get("refill")),
            "package": is_package(srv), "date": utcnow()}
    if d.get("ok"):
        doc = {**base, "order_id": d["order"], "api_charge": d.get("charge"), "status": "pending"}
        try:
            await smm_orders.insert_one(dict(doc))
        except Exception as e:
            await notify.alert_admins(f"🚨 SMM order {d['order']} (user <code>{uid}</code>) bought but NOT saved: {e!r}")
        await _record({"user_id": uid, "type": "smm", "title": srv["name"], "price": cost, "date": utcnow()})
        return {"kind": "ok", "order": doc, "balance": await get_balance(uid)}

    if st == 202 or d.get("error") in ("unconfirmed", "timeout"):
        # provider may have the order -> never auto-refund blindly
        await smm_orders.insert_one({**base, "order_id": None, "status": "unconfirmed"})
        await notify.alert_admins(
            f"🚨 <b>SMM order UNCONFIRMED</b>\nUser <code>{uid}</code> · Service {sid} · Qty {qty} · Charged ₹{cost:g}\n"
            "Check the Quick Codes / provider order list. If it does not exist, refund with /credit.")
        return {"kind": "unconfirmed"}

    await refund(uid, cost)
    kind, text = await explain("smm", st, d)
    return {"kind": kind, "text": text}


async def smm_sync_order(o):
    """-> (fresh_doc, refunded_now_amount)"""
    if o.get("order_id") is None:
        return o, 0.0
    st, d = await qc("smm", "GET", f"/v1/smm/order/{o['order_id']}")
    if not d.get("ok"):
        return o, 0.0
    await smm_orders.update_one({"_id": o["_id"]}, {"$set": {
        "status": str(d.get("status") or o.get("status") or "").lower(),
        "start_count": d.get("start_count"), "remains": d.get("remains")}})
    got = 0.0
    if d.get("refunded") and not o.get("refunded"):
        api_ref = float(d.get("refund_amount") or 0)
        api_charge = float(d.get("charge") or o.get("api_charge") or 0)
        ratio = (o["cost"] / api_charge) if api_charge else 1.0
        amt = round(min(api_ref * ratio, o["cost"]), 2)
        r = await smm_orders.update_one({"_id": o["_id"], "refunded": {"$ne": True}},
                                        {"$set": {"refunded": True, "refund_amount": amt}})
        if r.modified_count and amt > 0:
            await refund(o["user_id"], amt)
            got = amt
    return (await smm_orders.find_one({"_id": o["_id"]})) or o, got


async def smm_refill(o):
    st, d = await qc("smm", "POST", f"/v1/smm/refill/{o['order_id']}")
    if d.get("ok") and d.get("refill"):
        await smm_orders.update_one({"_id": o["_id"]}, {"$set": {"refill_id": str(d["refill"])}})
        return True, f"♻️ Refill requested (ID {d['refill']})."
    return False, "❌ Refill failed: " + str(d.get("message") or "not allowed yet")[:150]


# =====================================================================
#                        admin: manual credit / debit
# =====================================================================
async def admin_credit(uid, amount):
    r = await users.update_one({"_id": uid}, {"$inc": {"balance": round(float(amount), 2)}})
    return r.matched_count == 1 if hasattr(r, "matched_count") else r.modified_count == 1


async def admin_debit(uid, amount):
    r = await users.update_one({"_id": uid}, [{"$set": {"balance": {"$max": [0, {"$subtract": ["$balance", round(float(amount), 2)]}]}}}])
    return r.matched_count == 1 if hasattr(r, "matched_count") else r.modified_count == 1
