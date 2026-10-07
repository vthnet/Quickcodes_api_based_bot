# Quick Codes Reseller Bot

A Telegram reseller bot powered by the Quick Codes API.

This project allows you to run your own Telegram-based reseller system with support for Telegram accounts, OTP services, WhatsApp accounts, SMM services, wallet management, payments, orders, refunds, and an admin panel.

---

## Features

- Telegram account purchasing
- OTP purchasing
- WhatsApp account purchasing
- SMM services
- User wallet system
- Recharge system
- Auto UPI payments
- Manual UPI payments
- Order history
- Automatic refund handling
- SMM order tracking
- SMM refill support
- Admin panel
- API key management
- Service ON/OFF controls
- Profit percentage configuration
- Live API balance checking
- MongoDB database
- Quick Codes API integration

---

# How the Bot Works

The bot works as a reseller layer between your users and the Quick Codes APIs.

Users interact with your Telegram bot.

The bot receives the request, checks the user's wallet, sends the request to the required Quick Codes API, and then returns the result to the user.

The basic flow is:

User → Your Telegram Bot → Quick Codes API → Service Provider

Your users do not need direct access to the Quick Codes APIs.

---

# Services

## Telegram Accounts

Telegram account purchases are processed through Quick Codes Server 2.

Users can select the available country/service, confirm the purchase, and receive the required account/order information through the bot.

The bot handles the wallet deduction and order status.

---

## All Apps OTP

OTP services are processed through Quick Codes Server 3.

Users can select the required application and country and then create an OTP order.

The bot handles the order flow, OTP retrieval, cancellation, timeout and applicable refund handling.

---

## WhatsApp Accounts

WhatsApp account purchases are also processed through Quick Codes Server 3.

The WhatsApp flow is separate from the normal OTP flow and provides WhatsApp accounts only.

The bot handles:

- Country selection
- Account purchase
- OTP/order handling
- Cancellation
- Refund handling where applicable

---

## SMM Panel

The SMM section uses the Quick Codes SMM API.

Users can:

- Browse services
- Select a service
- Enter a target link
- Select quantity
- Check the price
- Place an order
- Check order status
- Request refill when available

The bot also handles supported cancelled, failed and partial order refunds.

---

# Requirements

Before installing the bot, you need:

- Python 3.10 or newer
- Telegram Bot Token
- MongoDB database
- Quick Codes API access
- Quick Codes API keys
- A server or hosting platform for 24/7 operation

For testing, you can run the bot locally on Windows.

---

# Installation

## 1. Download the Project

You can either clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
```

Then enter the project folder:

```bash
cd YOUR_REPOSITORY
```

Or download the repository using:

GitHub → Code → Download ZIP

Extract the ZIP after downloading.

---

# 2. Create a Virtual Environment

Windows PowerShell:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks the activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then activate again:

```powershell
.\.venv\Scripts\Activate.ps1
```

---

# 3. Install Requirements

Upgrade pip:

```powershell
python -m pip install --upgrade pip
```

Install the project requirements:

```powershell
pip install -r requirements.txt
```

Wait until all packages are installed successfully.

---

# 4. Create a Telegram Bot

Open Telegram and search for:

@BotFather

Send:

```text
/newbot
```

Follow the instructions provided by BotFather.

After creating the bot, you will receive a bot token.

Example:

```text
123456789:AAxxxxxxxxxxxxxxxxxxxxxxxx
```

Keep this token private.

Do not upload it to GitHub.

---

# 5. Create MongoDB Database

The bot uses MongoDB to store its own user and reseller information.

You can use MongoDB Atlas or another MongoDB provider.

Create a database and copy your MongoDB connection string.

Example:

```text
mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
```

Make sure your MongoDB configuration allows your server to connect.

---

# 6. Configure Environment Variables

The repository contains:

```text
.env.example
```

Create a new file named:

```text
.env
```

Copy the required values from `.env.example` into `.env`.

Your `.env` file contains private credentials and must never be uploaded to GitHub.

---

# Environment Configuration

The exact values depend on your setup.

Typical configuration includes:

```env
BOT_TOKEN=YOUR_BOT_TOKEN

ADMIN_IDS=YOUR_TELEGRAM_ID

DATABASE_URL=YOUR_MONGODB_CONNECTION_STRING

QC_API_BASE=YOUR_QUICK_CODES_API_URL
```

Use the variable names already provided in `.env.example`.

Do not rename environment variables unless you also update the source code.

---

# BOT_TOKEN

This is the Telegram bot token received from @BotFather.

Example:

```env
BOT_TOKEN=123456789:AAxxxxxxxxxxxxxxxx
```

Never share your real bot token publicly.

---

# ADMIN_IDS

This contains the Telegram ID of the bot administrator.

Example:

```env
ADMIN_IDS=123456789
```

If multiple administrator IDs are supported by your configuration, add them according to the format used in `.env.example`.

Use numeric Telegram IDs instead of usernames.

---

# DATABASE_URL

This is your MongoDB connection string.

Example:

```env
DATABASE_URL=mongodb+srv://username:password@cluster.mongodb.net/
```

Keep this private.

Anyone who obtains your MongoDB credentials may be able to access your database.

---

# Quick Codes API

This project requires Quick Codes API access.

The services are connected as follows:

| Service | API |
|---|---|
| Telegram Accounts | Quick Codes Server 2 |
| All Apps OTP | Quick Codes Server 3 |
| WhatsApp Accounts | Quick Codes Server 3 |
| SMM | Quick Codes SMM API |

You must have valid API access before using these services.

---

# API Key Setup

After starting the bot, open it using your administrator account.

Open:

```text
/admin
```

Then open the API key section.

Add the required Quick Codes API keys.

The bot uses these keys to communicate with the corresponding Quick Codes services.

Make sure you use the correct key for the correct service.

---

# API Key Security

Never publish your API keys.

Do not put real keys inside:

- README.md
- .env.example
- GitHub source code
- screenshots
- public messages
- public documentation

Real credentials should only be stored in your private environment configuration.

---

# Quick Codes Balance

The reseller bot uses the Quick Codes API to purchase services.

Your Quick Codes account must have enough balance for purchases.

There are two separate balances:

### User Balance

Money deposited by your users into your reseller bot.

### Quick Codes Balance

Your balance with Quick Codes, which is used to purchase services.

These are not the same balance.

Make sure your Quick Codes account has enough balance before enabling services for users.

---

# API Rate Limit

Quick Codes API requests are subject to the API limits of your account.

If you expect a large number of users or simultaneous orders, configure an appropriate API request limit in your Quick Codes account.

For example:

```text
/apilimit 600
```

Only use a limit supported by your Quick Codes account.

---

# Start the Bot

After configuring `.env`, start the bot with:

```powershell
python bot.py
```

If the configuration is correct, the bot will start and connect to Telegram.

Open your Telegram bot and send:

```text
/start
```

---

# Admin Panel

Administrators can open the admin panel using:

```text
/admin
```

The admin panel is used to manage the reseller system.

Depending on the enabled features, the admin panel can be used for:

- API keys
- Service settings
- Profit settings
- Payment settings
- User balance management
- Live API balances
- Service enable/disable controls
- Administrative management

---

# Service ON/OFF

Administrators can enable or disable services.

This is useful when:

- A provider is temporarily unavailable.
- You do not want to sell a particular service.
- Your provider balance is low.
- Maintenance is being performed.

When a service is disabled, users cannot place new orders for that service.

---

# Profit Settings

The admin panel allows you to configure your reseller profit.

The selling price is calculated using the provider price and your configured profit.

Example:

```text
Provider price: ₹100
Profit: 20%

Customer price: ₹120
```

Configure your profit according to your own pricing strategy.

---

# Live API Balance

The admin panel provides live balance information for the configured API services.

Use this section to monitor your provider balance.

If the provider balance becomes too low, recharge your Quick Codes account before accepting more orders.

---

# Payment System

The bot supports payment/recharge functionality.

Depending on your configuration, you can provide:

- Auto UPI
- Manual UPI

Both systems can be configured from the admin side.

---

# Auto UPI

The general Auto UPI flow is:

1. User opens the recharge section.
2. User selects Auto UPI.
3. User selects or enters the recharge amount.
4. The bot provides the payment information.
5. User completes the UPI payment.
6. User submits the required transaction information.
7. The payment is verified.
8. The user's wallet is credited after successful verification.

Make sure your Auto UPI credentials/configuration are correct before enabling it.

---

# Manual UPI

The general Manual UPI flow is:

1. User opens the recharge section.
2. User selects Manual UPI.
3. User receives the configured UPI details.
4. User makes the payment.
5. User submits the payment information.
6. User sends the required screenshot/details.
7. Admin reviews the payment.
8. Admin approves or rejects the request.
9. Balance is added after approval.

---

# User Wallet

Every reseller/user has their own wallet balance.

The wallet is used to pay for:

- Telegram accounts
- OTP services
- WhatsApp accounts
- SMM services

Users can also view their wallet balance and previous activity from the bot.

---

# Order History

Users can view their previous orders from the bot.

Order information can include:

- Service
- Order information
- Price
- Status
- Other information returned by the provider

This makes it easier for users to track their purchases.

---

# Refund System

The bot contains refund handling for supported failed, cancelled, expired and partial orders.

For example, if an order cannot be completed, the applicable amount can be returned to the user's wallet.

For SMM partial orders, the refund can be calculated according to the amount that was not delivered.

Do not manually refund users unless you have checked the actual order/payment status first.

---

# Admin Credit

Administrators can manually add balance to a user's wallet when required.

Use the admin functionality provided inside the bot.

Always verify the user's Telegram ID before changing their balance.

---

# Admin Debit

Administrators can also remove balance from a user's wallet when required.

Always double-check:

- User ID
- Amount
- Reason

before performing a manual balance adjustment.

---

# Testing Before Production

After installation, test everything before giving the bot to real users.

Recommended testing order:

## 1. Start the bot

```powershell
python bot.py
```

## 2. Test admin access

```text
/admin
```

## 3. Configure API keys

Add your Quick Codes API keys.

## 4. Check API balance

Make sure the API credentials are working.

## 5. Configure profit

Set your required profit percentage.

## 6. Configure payments

Set up Auto UPI and/or Manual UPI.

## 7. Enable services

Enable only the services you are ready to provide.

## 8. Test with another Telegram account

Test:

- Start
- Wallet
- Recharge
- Telegram purchase
- OTP purchase
- WhatsApp purchase
- SMM purchase
- Order history
- Refund handling

Do not start accepting real users until you have tested the complete flow.

---

# Deployment

The bot can be deployed on a server or hosting platform that supports Python.

Your hosting environment must provide:

- Python
- Internet access
- Environment variables
- MongoDB access
- Telegram API access
- Quick Codes API access

For production, do not store private credentials directly inside Python files.

Use environment variables instead.

---

# Running Locally on Windows

Open PowerShell and go to your project folder:

```powershell
cd "C:\Path\To\ResellerBot"
```

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install requirements:

```powershell
pip install -r requirements.txt
```

Start the bot:

```powershell
python bot.py
```

---

# Updating the Bot

If you installed the project using Git, update it with:

```powershell
git pull
```

If the update contains new dependencies:

```powershell
pip install -r requirements.txt
```

Then restart the bot:

```powershell
python bot.py
```

---

# Troubleshooting

## Bot is not starting

Check:

- BOT_TOKEN
- ADMIN_IDS
- DATABASE_URL
- Quick Codes API configuration
- Python version
- Installed dependencies

Then run:

```powershell
python bot.py
```

and check the complete terminal error.

---

## MongoDB Error

Check:

- MongoDB URL
- Username
- Password
- Database access
- Network access
- MongoDB cluster status

Make sure your MongoDB server allows the machine running the bot to connect.

---

## API Key Error

Open:

```text
/admin
```

and check your API key configuration.

Make sure the correct API key is being used for the correct service.

---

## Service Not Working

Possible reasons:

- Service is disabled
- Provider is unavailable
- Provider has no stock
- Quick Codes balance is insufficient
- API key is invalid
- API request limit has been reached
- Temporary API/network issue

Check the admin panel and Quick Codes account before making changes to the bot.

---

## Payment Not Working

Check:

- Payment method is enabled
- UPI details are correct
- Auto UPI configuration is correct
- Manual payment configuration is correct
- Required credentials are present

Never share payment credentials publicly while asking for support.

---

# Security

This is extremely important.

Never upload private credentials to GitHub.

Never commit:

```text
.env
```

Your `.gitignore` should include:

```gitignore
.env
.env.*
!.env.example

__pycache__/
*.py[cod]

.venv/
venv/
env/

.vscode/
.idea/

*.log

*.db
*.sqlite
*.sqlite3

secrets/
credentials/

.DS_Store
Thumbs.db
```

Before pushing the project to GitHub, run:

```powershell
git status
```

Make sure your private `.env` file is not being uploaded.

---

# Important Security Warning

If you accidentally upload any of these to GitHub:

- Telegram bot token
- Quick Codes API key
- MongoDB credentials
- Payment credentials
- Email passwords

do not simply delete the file and assume it is secure.

Immediately rotate/revoke the exposed credential and replace it with a new one.

---

# Project Structure

The project is divided into separate modules for easier maintenance.

```text
ResellerBot/
│
├── bot.py
├── config.py
├── db.py
├── admin.py
├── home.py
├── tg.py
├── otp.py
├── smm.py
├── payments.py
├── recharge.py
├── qc.py
├── flows.py
├── notify.py
├── flags.py
├── utils.py
│
├── requirements.txt
├── .env.example
└── README.md
```

The exact files may change in future releases.

---

# Support

If you downloaded this project and face any issue during installation, configuration or usage, contact:

**Telegram: @valriks**

When contacting support, please provide:

1. The exact error message.
2. The command you used.
3. Your Python version.
4. Your operating system.
5. What you were trying to do when the error occurred.

Example:

```text
Python: 3.11
OS: Windows

Command:
python bot.py

Error:
[paste your complete error here]
```

Do not send private credentials.

Never send:

- Bot token
- API keys
- MongoDB password
- MongoDB connection string
- Payment credentials
- Email passwords

Only send the error/log required to identify the problem.

---

# Disclaimer

This project is provided as source code for users who want to run their own reseller bot.

You are responsible for:

- Your Telegram bot
- Your Quick Codes account
- Your API keys
- Your MongoDB database
- Your payment configuration
- Your users
- Your pricing
- Your hosting
- Your use of third-party services

Make sure you follow the rules and terms of the services and APIs you use.

---

# Credits

Powered by Quick Codes API.

Developed for Telegram reseller automation.

---

# Quick Start

For experienced users, the basic setup is:

```powershell
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git

cd YOUR_REPOSITORY

python -m venv .venv

.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt

copy .env.example .env
```

Configure `.env`, then run:

```powershell
python bot.py
```

Open the bot in Telegram and configure the admin panel.

---

# Support

Need help?

Contact:

**@valriks**
