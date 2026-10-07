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



"""Admin alerts (no aiogram import here so the money flows stay testable)."""
import time
from config import ADMIN_IDS

_bot = None
_sent = {}


def set_bot(b):
    global _bot
    _bot = b


def get_bot():
    return _bot


async def alert_admins(text, key=None, every=600):
    now = time.time()
    if key:
        if now - _sent.get(key, 0) < every:
            return
        _sent[key] = now
    if _bot is None:
        print("[alert]", text)
        return
    for a in ADMIN_IDS:
        try:
            await _bot.send_message(a, text, parse_mode="HTML")
        except Exception:
            pass
