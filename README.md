# Reseller Bot (runs on the Quick Codes API)

Services: Buy Telegram account (Server 2) · All apps OTP / VTH panel (Server 3) · WhatsApp account (Server 3, WhatsApp only) · Social media services (SMM).
Users, wallet, recharge and history live in THIS bot's own MongoDB. Every purchase is paid from YOUR Quick Codes wallet through the API.

## Setup (10 minutes)
1. Create a bot with @BotFather, copy the token.
2. Create a free MongoDB (Atlas) for this bot, copy its connection string.
3. Copy `.env.example` to `.env` and fill it (BOT_TOKEN, ADMIN_IDS, DATABASE_URL, QC_API_BASE).
4. `pip install -r requirements.txt`
5. `python bot.py`
6. In Telegram open your bot and send `/admin`:
   - **🔑 API Keys** - paste your 3 keys from the Quick Codes bot (🔑 API Keys button). The key is checked and your message deleted.
   - **📈 Profit %** - set your profit for Server 2, Server 3 (OTP + WhatsApp) and SMM. Your price = Quick Codes price + that %.
   - **💳 Payments** - Auto UPI ID, UTR API URL / mail / app password, Manual UPI ID, Manual QR. Turn Auto / Manual ON.
   - **🛎 Services ON/OFF** - switch any service for your users.
   - **💰 Live Balances** - shows your Quick Codes wallet. Keep it recharged (in the Quick Codes bot).
7. Admin commands: `/admin` · `/credit user_id amount` · `/debit user_id amount`

## Important
- **Raise the API limit.** Quick Codes allows 60 requests/min per key by default. In the Quick Codes bot send `/apilimit 600` so many users can wait for OTPs at once.
- If your Quick Codes wallet runs out, users see "temporarily unavailable" (never charged) and you get an alert.
- Failed / timed-out / cancelled orders are refunded to the user's wallet automatically. SMM cancelled or partial orders too (the refund keeps your profit % in proportion).
- Do not share your API keys or `.env`.
