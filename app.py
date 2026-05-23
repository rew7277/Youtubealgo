import os
import json
import re
from flask import Flask, render_template_string, request, jsonify
from groq import Groq

app = Flask(__name__)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>YouTube SEO Growth Tool</title>
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet"/>
  <style>
    :root {
      --bg: #0a0a0f; --surface: #13131a; --surface2: #1a1a24;
      --border: #2a2a3a; --red: #ff3333; --red2: #ff6060;
      --gold: #ffd700; --text: #e8e8f0; --muted: #888899;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: var(--bg); color: var(--text); font-family: "Space Grotesk", sans-serif; min-height: 100vh; padding: 30px 20px; }
    .grid-bg {
      position: fixed; inset: 0; z-index: 0;
      background-image: linear-gradient(rgba(255,51,51,0.04) 1px, transparent 1px),
                        linear-gradient(90deg, rgba(255,51,51,0.04) 1px, transparent 1px);
      background-size: 40px 40px;
    }
    .container { max-width: 900px; margin: 0 auto; position: relative; z-index: 1; }
    header { text-align: center; margin-bottom: 40px; }
    .logo { font-size: 14px; font-family: "JetBrains Mono", monospace; color: var(--red); letter-spacing: 4px; text-transform: uppercase; margin-bottom: 12px; }
    h1 { font-size: clamp(28px, 5vw, 48px); font-weight: 700; line-height: 1.1; }
    h1 span { color: var(--red); }
    .subtitle { color: var(--muted); margin-top: 10px; font-size: 15px; }
    .form-card { background: var(--surface); border: 1px solid var(--border); border-radius: 20px; padding: 32px; margin-bottom: 32px; }
    .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
    label { display: block; font-size: 12px; font-family: "JetBrains Mono", monospace; color: var(--muted); text-transform: uppercase; letter-spacing: 2px; margin-bottom: 8px; }
    input, textarea {
      width: 100%; padding: 14px 16px;
      background: var(--surface2); border: 1px solid var(--border);
      border-radius: 12px; color: var(--text);
      font-family: "Space Grotesk", sans-serif; font-size: 15px;
      transition: border-color 0.2s; outline: none;
    }
    input:focus, textarea:focus { border-color: var(--red); }
    .btn {
      display: flex; align-items: center; justify-content: center; gap: 10px;
      width: 100%; padding: 16px; margin-top: 24px;
      background: var(--red); color: #fff; border: none;
      border-radius: 14px; font-size: 16px; font-weight: 700;
      font-family: "Space Grotesk", sans-serif; cursor: pointer; transition: all 0.2s;
    }
    .btn:hover { background: var(--red2); transform: translateY(-1px); }
    .btn:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
    .spinner { display: none; width: 20px; height: 20px; border: 3px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .results { display: none; }
    .section { background: var(--surface); border: 1px solid var(--border); border-radius: 20px; padding: 28px; margin-bottom: 24px; }
    .section-label { font-size: 11px; font-family: "JetBrains Mono", monospace; color: var(--red); letter-spacing: 3px; text-transform: uppercase; margin-bottom: 16px; }
    .title-item { padding: 12px 16px; background: var(--surface2); border-radius: 10px; margin-bottom: 10px; border-left: 3px solid var(--red); display: flex; justify-content: space-between; align-items: center; gap: 12px; }
    .copy-btn { background: var(--border); border: none; color: var(--muted); padding: 6px 12px; border-radius: 8px; cursor: pointer; font-size: 12px; font-family: "JetBrains Mono", monospace; white-space: nowrap; transition: all 0.15s; }
    .copy-btn:hover { background: var(--red); color: #fff; }
    .copy-btn.copied { background: #22c55e; color: #fff; }
    pre { font-family: "JetBrains Mono", monospace; font-size: 13px; line-height: 1.7; white-space: pre-wrap; color: var(--text); background: var(--surface2); padding: 18px; border-radius: 12px; }
    .hashtags-wrap { display: flex; flex-wrap: wrap; gap: 8px; }
    .hashtag { background: var(--surface2); border: 1px solid var(--border); color: var(--red2); padding: 6px 14px; border-radius: 999px; font-size: 13px; font-family: "JetBrains Mono", monospace; }
    .ideas-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .idea-item { padding: 12px 14px; background: var(--surface2); border-radius: 10px; font-size: 14px; border-left: 2px solid var(--gold); color: var(--text); }
    .idea-num { color: var(--gold); font-weight: 700; margin-right: 6px; font-family: "JetBrains Mono", monospace; }
    .checklist-item { display: flex; gap: 10px; padding: 10px 0; border-bottom: 1px solid var(--border); font-size: 14px; }
    .checklist-item:last-child { border-bottom: none; }
    .check-icon { color: #22c55e; flex-shrink: 0; font-size: 16px; }
    .copy-all { display: flex; align-items: center; gap: 8px; background: var(--surface2); border: 1px solid var(--border); color: var(--muted); padding: 8px 16px; border-radius: 10px; cursor: pointer; font-size: 13px; font-family: "JetBrains Mono", monospace; float: right; margin-bottom: 12px; transition: all 0.15s; }
    .copy-all:hover { border-color: var(--red); color: var(--red); }
    .error-box { background: rgba(255,51,51,0.1); border: 1px solid rgba(255,51,51,0.3); color: var(--red2); padding: 16px; border-radius: 12px; display: none; margin-top: 16px; }
    @media(max-width:600px) { .form-grid { grid-template-columns: 1fr; } .ideas-grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <div class="grid-bg"></div>
  <div class="container">
    <header>
      <div class="logo">// YouTube Growth Tool</div>
      <h1>AI-Powered <span>SEO</span> Assistant</h1>
      <p class="subtitle">Generate titles, descriptions, hashtags & 30 Shorts ideas — powered by Groq AI</p>
    </header>
    <div class="form-card">
      <div class="form-grid">
        <div>
          <label>YouTube Handle</label>
          <input id="handle" placeholder="@YourChannel" />
        </div>
        <div>
          <label>Video / Shorts URL</label>
          <input id="url" placeholder="https://youtube.com/shorts/..." />
        </div>
        <div>
          <label>Topic / Niche</label>
          <input id="topic" placeholder="e.g. Telugu comedy, Chennai lifestyle, cooking..." />
        </div>
        <div>
          <label>Target Keywords</label>
          <input id="keywords" placeholder="e.g. telugu shorts, funny, viral, village girl..." />
        </div>
      </div>
      <div class="error-box" id="errorBox"></div>
      <button class="btn" id="generateBtn" onclick="generate()">
        <span id="btnText">🚀 Generate SEO Plan</span>
        <div class="spinner" id="spinner"></div>
      </button>
    </div>
    <div class="results" id="results">
      <div class="section">
        <div class="section-label">▸ SEO Titles</div>
        <div id="titlesOut"></div>
      </div>
      <div class="section">
        <div class="section-label">▸ Video Description</div>
        <button class="copy-all" onclick="copyEl(\'descOut\')">📋 Copy All</button>
        <pre id="descOut"></pre>
      </div>
      <div class="section">
        <div class="section-label">▸ Hashtags</div>
        <div class="hashtags-wrap" id="hashtagsOut"></div>
      </div>
      <div class="section">
        <div class="section-label">▸ Pinned Comment</div>
        <button class="copy-all" onclick="copyEl(\'pinnedOut\')">📋 Copy</button>
        <pre id="pinnedOut"></pre>
      </div>
      <div class="section">
        <div class="section-label">▸ 30 Shorts Ideas</div>
        <div class="ideas-grid" id="ideasOut"></div>
      </div>
      <div class="section">
        <div class="section-label">▸ Upload Checklist</div>
        <div id="checklistOut"></div>
      </div>
    </div>
  </div>
  <script>
    async function generate() {
      const handle   = document.getElementById("handle").value.trim();
      const url      = document.getElementById("url").value.trim();
      const topic    = document.getElementById("topic").value.trim();
      const keywords = document.getElementById("keywords").value.trim();
      const errBox   = document.getElementById("errorBox");
      errBox.style.display = "none";
      if (!handle || !url || !topic) {
        errBox.textContent = "Please fill in Handle, URL, and Topic.";
        errBox.style.display = "block"; return;
      }
      const btn = document.getElementById("generateBtn");
      btn.disabled = true;
      document.getElementById("btnText").textContent = "Generating...";
      document.getElementById("spinner").style.display = "block";
      document.getElementById("results").style.display = "none";
      try {
        const res  = await fetch("/generate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ handle, url, topic, keywords }) });
        const data = await res.json();
        if (data.error) throw new Error(data.error);
        renderResults(data);
      } catch (e) {
        errBox.textContent = "Error: " + e.message;
        errBox.style.display = "block";
      } finally {
        btn.disabled = false;
        document.getElementById("btnText").textContent = "🚀 Generate SEO Plan";
        document.getElementById("spinner").style.display = "none";
      }
    }
    function renderResults(d) {
      document.getElementById("titlesOut").innerHTML = (d.titles||[]).map(t =>
        `<div class="title-item"><span>${t}</span><button class="copy-btn" onclick="copyStr(this,'${t.replace(/'/g,"\\'").replace(/"/g,"&quot;")}')">Copy</button></div>`).join("");
      document.getElementById("descOut").textContent    = d.description    || "";
      document.getElementById("hashtagsOut").innerHTML  = (d.hashtags||[]).map(h => `<span class="hashtag">${h}</span>`).join("");
      document.getElementById("pinnedOut").textContent  = d.pinned_comment  || "";
      document.getElementById("ideasOut").innerHTML     = (d.ideas||[]).map((v,i) => `<div class="idea-item"><span class="idea-num">${i+1}.</span>${v}</div>`).join("");
      document.getElementById("checklistOut").innerHTML = (d.checklist||[]).map(v => `<div class="checklist-item"><span class="check-icon">✓</span><span>${v}</span></div>`).join("");
      document.getElementById("results").style.display = "block";
      document.getElementById("results").scrollIntoView({ behavior: "smooth" });
    }
    function copyEl(id)        { navigator.clipboard.writeText(document.getElementById(id).textContent); }
    function copyStr(btn, txt) {
      navigator.clipboard.writeText(txt);
      btn.textContent = "Copied!"; btn.classList.add("copied");
      setTimeout(() => { btn.textContent = "Copy"; btn.classList.remove("copied"); }, 2000);
    }
  </script>
</body>
</html>'''


def extract_video_type(url):
    return "Short" if "shorts" in (url or "").lower() else "Video"


def generate_seo_plan(handle, url, topic, keywords):
    video_type = extract_video_type(url)
    prompt = f"""You are a YouTube SEO expert. Generate a complete SEO growth plan.

Channel Handle: {handle}
Video URL: {url}
Video Type: {video_type}
Topic / Niche: {topic}
Target Keywords: {keywords}

Return ONLY a valid JSON object — no markdown, no explanation, no backticks. Raw JSON only:
{{
  "titles": ["title1","title2","title3","title4","title5"],
  "description": "full video description with keywords, call to action, and hashtags",
  "hashtags": ["#tag1","#tag2","#tag3","#tag4","#tag5","#tag6","#tag7","#tag8","#tag9","#tag10","#tag11","#tag12","#tag13","#tag14","#tag15"],
  "pinned_comment": "engaging pinned comment",
  "ideas": ["idea1","idea2","...30 total"],
  "checklist": ["tip1","tip2","...12 total"]
}}

- All 5 titles must be curiosity-driven and SEO-rich for this specific topic
- All 30 ideas must be unique and tailored to this niche
- Return ONLY the JSON object, nothing else"""

    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=4096,
    )
    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"^```\s*",     "", raw)
    raw = re.sub(r"\s*```$",     "", raw)
    return json.loads(raw)


@app.route("/favicon.ico")
def favicon():
    return "", 204


@app.route("/")
def home():
    return render_template_string(HTML)


@app.route("/generate", methods=["POST"])
def generate():
    data     = request.get_json()
    handle   = data.get("handle",   "").strip()
    url      = data.get("url",      "").strip()
    topic    = data.get("topic",    "").strip()
    keywords = data.get("keywords", "").strip()

    if not all([handle, url, topic]):
        return jsonify({"error": "Handle, URL, and Topic are required."}), 400

    try:
        result = generate_seo_plan(handle, url, topic, keywords)
        return jsonify(result)
    except json.JSONDecodeError:
        return jsonify({"error": "AI returned invalid response. Please try again."}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
