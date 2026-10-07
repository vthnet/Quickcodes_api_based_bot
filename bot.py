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


import asyncio
import logging
from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, QC_API_BASE, ADMIN_IDS
from db import users, init_indexes, get_settings, utcnow
import notify
import admin, recharge, tg, otp, smm, home

logging.basicConfig(level=logging.INFO)


class UserMiddleware(BaseMiddleware):
    """every user gets a wallet the first time we see them"""
    async def __call__(self, handler, event, data):
        u = getattr(event, "from_user", None)
        if u and not u.is_bot:
            doc = await users.find_one({"_id": u.id}, {"username": 1})
            if doc is None:
                try:
                    await users.insert_one({"_id": u.id, "balance": 0.0, "username": u.username,
                                            "name": u.full_name, "joined": utcnow()})
                except Exception:
                    pass
            elif doc.get("username") != u.username:
                await users.update_one({"_id": u.id}, {"$set": {"username": u.username, "name": u.full_name}})
        return await handler(event, data)


async def main():
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.message.outer_middleware(UserMiddleware())
    dp.callback_query.outer_middleware(UserMiddleware())

    # admin first so its text prompts always win
    for r in (admin.router, recharge.router, tg.router, otp.router, smm.router, home.router):
        dp.include_router(r)

    notify.set_bot(bot)
    await init_indexes()
    s = await get_settings()
    missing = [k for k, v in s["api_keys"].items() if not v]
    print(f"[bot] Quick Codes API: {QC_API_BASE}")
    if missing:
        print(f"[bot] !!! API keys not set yet for: {', '.join(missing)}  ->  send /admin → API Keys")

    bg = [asyncio.create_task(otp.otp_loop()), asyncio.create_task(smm.smm_loop())]
    try:
        await bot.delete_webhook(drop_pending_updates=False)
        me = await bot.get_me()
        print(f"[bot] @{me.username} is running. Admins: {ADMIN_IDS}")
        await dp.start_polling(bot)
    finally:
        for t in bg:
            t.cancel()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
