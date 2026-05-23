# YouTube SEO Growth Tool 🚀
AI-powered YouTube SEO assistant using **Groq (Free API)** — generates titles, descriptions, hashtags, pinned comments, 30 Shorts ideas, and upload checklist.

## Run Locally

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/yt-seo-tool.git
cd yt-seo-tool
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set your Groq API key
Get your free key at: https://console.groq.com

```bash
# Mac / Linux
export GROQ_API_KEY=your_key_here

# Windows CMD
set GROQ_API_KEY=your_key_here

# Windows PowerShell
$env:GROQ_API_KEY="your_key_here"
```

### 4. Run
```bash
python app.py
```
Open: http://127.0.0.1:5000

---

## Deploy to Railway.app

1. Push this repo to GitHub
2. Go to https://railway.app → **New Project** → **Deploy from GitHub repo**
3. Select your repo
4. Go to **Variables** tab → Add:
   ```
   GROQ_API_KEY = your_groq_key_here
   ```
5. Railway auto-detects `Procfile` and deploys ✅
6. Click **Generate Domain** to get your public URL

---

## Project Structure
```
yt-seo-tool/
├── app.py              ← Flask backend (Groq AI)
├── templates/
│   └── index.html      ← Frontend UI
├── requirements.txt    ← groq, flask, gunicorn
├── Procfile            ← Railway start command
├── railway.json        ← Railway config
└── README.md
```

## What It Generates
| Output | Details |
|--------|---------|
| SEO Titles | 5 curiosity-driven, keyword-rich titles |
| Description | Full description with keywords + CTA |
| Hashtags | 15 relevant hashtags |
| Pinned Comment | Engagement-boosting comment template |
| Shorts Ideas | 30 unique ideas for your niche |
| Checklist | 12 upload & growth best practices |

## Groq Free Tier Limits
- 14,400 requests/day
- 30 requests/minute
- Model: `llama3-70b-8192` (fast & accurate)
- **No credit card required**
