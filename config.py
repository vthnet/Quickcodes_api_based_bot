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


import os
from dotenv import load_dotenv

load_dotenv()


def _need(name):
    v = os.getenv(name, "").strip()
    if not v:
        raise RuntimeError(f"Missing required setting in .env: {name}")
    return v


BOT_TOKEN = _need("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in _need("ADMIN_IDS").replace(" ", "").split(",") if x]
DATABASE_URL = _need("DATABASE_URL")                       # your own MongoDB for THIS bot
DB_NAME = os.getenv("DB_NAME", "reseller_bot")
QC_API_BASE = _need("QC_API_BASE").rstrip("/")             # Quick Codes API address, e.g. https://api.example.com

BOT_TITLE = os.getenv("BOT_TITLE", "MULTI SERVICE BOT")   # name shown on the home screen
SUPPORT_LINK = os.getenv("SUPPORT_LINK", "").strip()      # optional "Contact Support" button on payment problems
