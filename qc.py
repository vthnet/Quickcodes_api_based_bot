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

"""Quick Codes API client + friendly error handling."""
import asyncio
from html import escape
import ssl
import aiohttp
import certifi
from config import QC_API_BASE
from db import get_settings
import notify

_session = None
BUSY_USER = "⚠️ <b>Service temporarily unavailable.</b>\nPlease try again later. <i>You were not charged.</i>"


async def _sess():
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=40),
            connector=aiohttp.TCPConnector(ssl=ssl.create_default_context(cafile=certifi.where()), limit=30, ttl_dns_cache=300))
    return _session


async def qc(server, method, path, params=None, json=None, timeout=30, key=None):
    """-> (http_status, dict). http_status 0 = could not reach the API at all."""
    if key is None:
        key = ((await get_settings())["api_keys"].get(server) or "").strip()
    if not key:
        return 0, {"ok": False, "error": "no_key", "message": "API key is not set"}
    try:
        s = await _sess()
        async with s.request(method, QC_API_BASE + path, params=params, json=json,
                             headers={"X-API-Key": key}, timeout=aiohttp.ClientTimeout(total=timeout)) as r:
            try:
                data = await r.json(content_type=None)
            except Exception:
                data = {"ok": False, "error": "bad_response", "message": "Invalid response from API"}
            if not isinstance(data, dict):
                data = {"ok": False, "error": "bad_response", "message": "Invalid response from API"}
            return r.status, data
    except asyncio.TimeoutError:
        # the request may or may not have been processed -> callers treat money actions carefully
        return 0, {"ok": False, "error": "timeout", "message": "API did not answer in time"}
    except aiohttp.ClientError as e:
        return 0, {"ok": False, "error": "network", "message": f"Cannot reach API: {e!r}"}
    except Exception as e:
        return 0, {"ok": False, "error": "network", "message": f"{e!r}"}


NAMES = {"s2": "Server 2 (Telegram accounts)", "s3": "Server 3 (OTP / WhatsApp)", "smm": "SMM Panel"}


async def explain(server, status, data):
    """-> (kind, user_text). Also alerts the admin when the problem is on the reseller side."""
    err = (data or {}).get("error")
    if err == "out_of_stock":
        return "stock", "❌ <b>Out of stock.</b> No numbers available right now.\n<i>You were not charged.</i>"
    if err == "insufficient_balance":
        await notify.alert_admins(
            f"🚨 <b>Your Quick Codes wallet is too low</b> ({NAMES[server]}).\n"
            f"Needed: ₹{data.get('price', '?')} · Balance: ₹{data.get('balance', '?')}\n"
            "Recharge it in the Quick Codes bot, users cannot buy until then.", key=f"funds:{server}")
        return "funds", BUSY_USER
    if err in ("invalid_api_key", "missing_api_key", "wrong_server_key", "banned", "no_key"):
        await notify.alert_admins(
            f"🚨 <b>API key problem</b> - {NAMES[server]}\n<code>{(data or {}).get('message')}</code>\n"
            "Set a valid key: /admin → API Keys.", key=f"auth:{server}")
        return "auth", BUSY_USER
    if err in ("service_disabled", "maintenance"):
        return "maint", "⚠️ This service is under maintenance. Please try again later!\n<i>You were not charged.</i>"
    if err in ("provider_rejected", "bad_request", "bad_quantity", "service_not_found", "country_not_found"):
        return "reject", "❌ " + escape(str((data or {}).get("message") or "Order rejected."))
    if err == "rate_limited":
        return "busy", "⚠️ Too many requests. Please try again in a few seconds.\n<i>You were not charged.</i>"
    if status == 0:
        await notify.alert_admins(f"⚠️ Cannot reach the Quick Codes API for {NAMES[server]}.\n"
                                  f"<code>{(data or {}).get('message')}</code>", key=f"net:{server}", every=300)
        return "network", BUSY_USER
    return "other", "⚠️ <b>Server busy.</b> Please try again shortly.\n<i>You were not charged.</i>"
