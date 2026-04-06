# ✨ CANTARELLA – AniwatchTv Downloader Bot

> A powerful & premium Telegram bot to search, stream & download anime directly from Aniwatch — built for speed, automation, and a beautiful UI.

---

## 💥 Features

| Feature | Details |
|---|---|
| 🔍 Search | Advanced anime search with instant results |
| 📥 Download | Multi-quality: 360p / 480p / 720p / 1080p |
| ⚡️ Progress UI | Live download & upload progress bar |
| 🗓 Schedule | Today's airing anime in IST timezone |
| 🔔 Tracking | Auto-notify when new episodes drop |
| 💬 Force-Sub | Force users to join channel(s) before use |
| 🧹 Auto-Delete | Auto-delete files after set time (/autodel) |
| 🍔 Manage Panel | Inline admin management (/manage) |
| 📊 Stats & Ping | Live stats, latency, uptime |
| 🔄 Restart | Hot restart from Telegram (/restart) |

---

## 🚀 Deploy on Railway (Recommended)

### Step 1 – Fork / Push to GitHub
Push this repo to your GitHub account.

### Step 2 – Create Railway Project
1. Go to [railway.app](https://railway.app) → **New Project**
2. Select **Deploy from GitHub repo**
3. Choose your forked repo

### Step 3 – Add Environment Variables
In Railway → your service → **Variables**, add:

| Variable | Description |
|---|---|
| `BOT_TOKEN` | From [@BotFather](https://t.me/BotFather) |
| `OWNER_ID` | Your Telegram user ID (get from @userinfobot) |
| `MONGO_URI` | MongoDB Atlas connection string |
| `LOG_CHANNEL` | Channel ID for logs (e.g. -1001234567890) |
| `FORCE_SUB_CHANNEL` | @username of required channel |
| `ADMINS` | Space-separated extra admin user IDs |

### Step 4 – Deploy
Railway auto-deploys. Your bot is live! ✅

---

## 🗄️ MongoDB Setup (Free)

1. Go to [mongodb.com/atlas](https://www.mongodb.com/atlas)
2. Create free cluster → **Connect** → **Drivers**
3. Copy the connection string → paste as `MONGO_URI`

---

## 💻 Local Setup

```bash
git clone https://github.com/abhinai2244/AniwatchTvdl.git
cd AniwatchTvdl

# Copy env file
cp .env.example .env
# Fill in your values in .env

# Install dependencies
pip install -r requirements.txt

# Run
python bot.py
```

---

## 📋 Commands

### User Commands
| Command | Description |
|---|---|
| `/start` | Welcome message |
| `/help` | Command guide |
| `/search <name>` | Search anime |
| `/schedule` | Today's airing schedule (IST) |
| `/track <name>` | Auto-notify for new episodes |
| `/untrack <name>` | Remove tracking |
| `/autodel <min>` | Set auto-delete timer |
| `/ping` | Bot latency & uptime |

### Admin Commands
| Command | Description |
|---|---|
| `/manage` | Inline management panel |
| `/stats` | Full bot statistics |
| `/broadcast <msg>` | Message all users |
| `/ban <user_id>` | Ban a user |
| `/unban <user_id>` | Unban a user |
| `/addadmin <id>` | Add admin |
| `/removeadmin <id>` | Remove admin |
| `/restart` | Restart the bot |
| `/logs` | Download bot logs |

---

## 📁 Project Structure

```
AniwatchTvdl/
├── bot.py              ← Entry point
├── config.py           ← All configuration
├── requirements.txt
├── Procfile            ← Railway / Heroku
├── railway.json        ← Railway config
├── .env.example        ← Environment template
├── database/
│   └── db.py           ← MongoDB (Motor async)
├── handlers/
│   ├── start.py        ← /start, /help
│   ├── search.py       ← Search + inline query
│   ├── download.py     ← Episode/server/quality/download
│   ├── admin.py        ← Admin commands
│   ├── manage.py       ← /manage panel
│   ├── schedule.py     ← /schedule, /track, /untrack
│   └── autodel.py      ← /autodel
└── utils/
    ├── aniwatch.py     ← Aniwatch API wrapper
    ├── downloader.py   ← yt-dlp + upload logic
    └── helpers.py      ← Force-sub, keyboards, guards
```

---

## ⭐ Support

Give a ⭐ star and fork for more repos!

Made with ❤️ — **CANTARELLA Bot**
