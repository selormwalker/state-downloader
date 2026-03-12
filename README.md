# STATE DOWNLOADER — Vercel Deploy

## Structure
```
state-downloader/
├── public/
│   └── index.html       ← Frontend
├── api/
│   └── cobalt.js        ← Serverless proxy (bypasses CORS, tries multiple instances)
├── vercel.json          ← Routing config
└── README.md
```

## Deploy in 3 steps

### 1. Push to GitHub
```bash
git init
git add .
git commit -m "STATE DOWNLOADER"
gh repo create state-downloader --public --push
```

### 2. Deploy to Vercel
Go to https://vercel.com/new → import your repo → click Deploy.
No build settings needed — Vercel auto-detects the structure.

### 3. Done
Your site is live at `https://your-project.vercel.app`

---

## Optional: Add your own Cobalt instance for max reliability
In Vercel dashboard → your project → Settings → Environment Variables:
```
COBALT_INSTANCE = https://your-cobalt-instance.example.com
```
This guarantees uptime and lets you set cookies for Instagram/etc.

### How to self-host Cobalt (takes ~5 min on any VPS):
```bash
git clone https://github.com/imputnet/cobalt
cd cobalt
cp .env.example .env
# Edit .env — set API_URL to your domain
docker compose up -d
```
