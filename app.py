import os, json, re, base64
import requests as http_req
from flask import Flask, render_template_string, request, jsonify
from groq import Groq

app    = Flask(__name__)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# ── helpers ──────────────────────────────────────────────────────────────────
def clean_json(raw):
    """Strip markdown fences and parse JSON. Handles ```json ... ``` blocks."""
    raw = raw.strip()
    # Remove opening fence (```json or ```)
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.DOTALL)
    # Remove trailing fence
    raw = re.sub(r"\s*```\s*$", "", raw, flags=re.DOTALL)
    return json.loads(raw.strip())

def groq_chat(prompt, temp=0.7, tokens=4096):
    r = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=temp, max_tokens=tokens)
    return r.choices[0].message.content

def groq_vision(b64, prompt, mime="image/jpeg"):
    r = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            {"type": "text", "text": prompt}
        ]}], max_tokens=2048)
    return r.choices[0].message.content

def yt_api(path, params, key):
    params["key"] = key
    r = http_req.get(f"https://www.googleapis.com/youtube/v3/{path}",
                     params=params, timeout=10)
    r.raise_for_status()
    return r.json()

# ── routes ───────────────────────────────────────────────────────────────────
@app.route("/favicon.ico")
def favicon(): return "", 204

@app.route("/")
def home(): return render_template_string(HTML)

# 1. SEO Generator
@app.route("/generate", methods=["POST"])
def generate():
    d = request.get_json()
    handle = d.get("handle", "").strip()
    url    = d.get("url", "").strip()
    topic  = d.get("topic", "").strip()
    kw     = d.get("keywords", "").strip()
    if not all([handle, url, topic]):
        return jsonify({"error": "Handle, URL and Topic are required."}), 400
    vtype = "Short" if "shorts" in url.lower() else "Video"
    prompt = f"""YouTube SEO expert. Generate a complete SEO plan.
Handle:{handle} URL:{url} Type:{vtype} Topic:{topic} Keywords:{kw}
Return ONLY raw JSON (no markdown):
{{"titles":["t1","t2","t3","t4","t5"],
  "description":"full description with CTA and hashtags",
  "hashtags":["#h1",...15 total],
  "pinned_comment":"engaging pinned comment",
  "ideas":["idea1",...30 unique ideas specific to this niche],
  "checklist":["tip1",...12 tips]}}"""
    try:
        return jsonify(clean_json(groq_chat(prompt)))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 2. Manual Analytics
@app.route("/analyse", methods=["POST"])
def analyse():
    d = request.get_json()
    if not d.get("niche") or not d.get("views"):
        return jsonify({"error": "Niche and Views are required."}), 400
    prompt = f"""Senior YouTube growth analyst. Brutal honest diagnosis.
Handle:{d.get('handle')} Niche:{d.get('niche')} Age:{d.get('age')}
Total videos:{d.get('total_videos')}
Last 28d — Views:{d.get('views')} Impressions:{d.get('impressions')}
CTR:{d.get('ctr')}% WatchTime:{d.get('watchtime')}h AvgDuration:{d.get('avd')}s
NewSubs:{d.get('subs')} TotalSubs:{d.get('total_subs')}
Likes:{d.get('likes')} Comments:{d.get('comments')}
TopVideos:{d.get('top_videos')} Traffic:{d.get('traffic')} Geo:{d.get('geo')}
Return ONLY raw JSON:
{{"score":<0-100>,
  "score_label":"<Early Stage|Struggling|Growing|Strong>",
  "score_summary":"2 honest sentences using their real numbers",
  "diagnosis":[{{"title":"...","severity":"critical|warning|ok","detail":"specific with numbers"}},...6 items],
  "fixes":[{{"action":"short title","detail":"exact step to do this week"}},...7 items],
  "opportunities":[{{"title":"...","detail":"how to exploit with specifics"}},...5 items],
  "best_post_times":"specific days/times based on their geo and niche",
  "roadmap":"Week 1:\\n...\\nWeek 2:\\n...\\nWeek 3:\\n...\\nWeek 4:\\n..."}}"""
    try:
        return jsonify(clean_json(groq_chat(prompt, temp=0.5)))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 3. YouTube API — auto fetch channel
@app.route("/fetch-channel", methods=["POST"])
def fetch_channel():
    d = request.get_json()
    handle = d.get("handle", "").strip().lstrip("@")
    yt_key = d.get("yt_key", "").strip()
    if not handle or not yt_key:
        return jsonify({"error": "Handle and YouTube API Key are required."}), 400
    try:
        ch = yt_api("channels", {"part": "statistics,snippet", "forHandle": f"@{handle}"}, yt_key)
        if not ch.get("items"):
            return jsonify({"error": "Channel not found. Check your handle."}), 404
        item  = ch["items"][0]
        stats = item["statistics"]
        snip  = item["snippet"]
        ch_id = item["id"]
        # fetch top 5 videos
        search  = yt_api("search", {"part": "snippet", "channelId": ch_id,
                                     "type": "video", "order": "viewCount", "maxResults": 5}, yt_key)
        vid_ids = ",".join(v["id"]["videoId"] for v in search.get("items", [])
                           if v.get("id", {}).get("videoId"))
        top_vids = []
        if vid_ids:
            vdata = yt_api("videos", {"part": "statistics,snippet", "id": vid_ids}, yt_key)
            for v in vdata.get("items", []):
                top_vids.append({
                    "title":    v["snippet"]["title"],
                    "views":    int(v["statistics"].get("viewCount", 0)),
                    "likes":    int(v["statistics"].get("likeCount", 0)),
                    "comments": int(v["statistics"].get("commentCount", 0)),
                })
        return jsonify({
            "name":        snip.get("title"),
            "description": snip.get("description", "")[:300],
            "subscribers": int(stats.get("subscriberCount", 0)),
            "total_views": int(stats.get("viewCount", 0)),
            "video_count": int(stats.get("videoCount", 0)),
            "country":     snip.get("country", "N/A"),
            "top_videos":  top_vids,
        })
    except http_req.exceptions.HTTPError as e:
        return jsonify({"error": f"YouTube API error: {e.response.status_code} — check your API key."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 4. Competitor analysis
@app.route("/competitor", methods=["POST"])
def competitor():
    d = request.get_json()
    handle   = d.get("handle", "").strip().lstrip("@")
    yt_key   = d.get("yt_key", "").strip()
    my_niche = d.get("my_niche", "").strip()
    if not handle or not yt_key:
        return jsonify({"error": "Competitor handle and YouTube API Key required."}), 400
    try:
        ch = yt_api("channels", {"part": "statistics,snippet", "forHandle": f"@{handle}"}, yt_key)
        if not ch.get("items"):
            return jsonify({"error": "Competitor channel not found."}), 404
        item  = ch["items"][0]
        stats = item["statistics"]
        ch_id = item["id"]
        search  = yt_api("search", {"part": "snippet", "channelId": ch_id,
                                     "type": "video", "order": "viewCount", "maxResults": 8}, yt_key)
        vid_ids = ",".join(v["id"]["videoId"] for v in search.get("items", [])
                           if v.get("id", {}).get("videoId"))
        top_vids = []
        if vid_ids:
            vdata = yt_api("videos", {"part": "statistics,snippet", "id": vid_ids}, yt_key)
            for v in vdata.get("items", []):
                top_vids.append(f'{v["snippet"]["title"]} — {v["statistics"].get("viewCount","?")} views')
        prompt = f"""YouTube competitive analyst.
Competitor: @{handle}  Subs:{stats.get('subscriberCount')}  TotalViews:{stats.get('viewCount')}  Videos:{stats.get('videoCount')}
Their top videos:
{chr(10).join(top_vids)}
My niche: {my_niche}
Return ONLY raw JSON:
{{"competitor_strengths":["...",...5 items],
  "competitor_weaknesses":["...",...4 items],
  "content_gaps":["topics they miss that I can own",...5 items],
  "winning_formats":["video formats that get them most views",...4 items],
  "steal_these_ideas":["specific video ideas I can do better",...6 items],
  "thumbnail_patterns":"what thumbnail style they use and why it works",
  "posting_frequency":"their estimated posting pattern",
  "action_plan":["concrete step 1","step 2",...5 steps to outrank them]}}"""
        return jsonify(clean_json(groq_chat(prompt, temp=0.5)))
    except http_req.exceptions.HTTPError as e:
        return jsonify({"error": f"YouTube API error {e.response.status_code}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 5. Thumbnail analyser (vision)
@app.route("/thumbnail", methods=["POST"])
def thumbnail():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded."}), 400
    f    = request.files["image"]
    mime = f.content_type or "image/jpeg"
    b64  = base64.b64encode(f.read()).decode()
    niche = request.form.get("niche", "YouTube")
    prompt = f"""You are a YouTube thumbnail expert. Analyse this thumbnail for a {niche} channel.
Return ONLY raw JSON:
{{"score":<0-100>,
  "grade":"<A|B|C|D|F>",
  "summary":"2 sentence overall verdict",
  "strengths":[{{"point":"...","detail":"..."}},...3 items],
  "weaknesses":[{{"point":"...","detail":"..."}},...3 items],
  "ctr_prediction":"<Very Low|Low|Average|High|Very High> — explain why",
  "color_analysis":"are the colors eye-catching on dark/light feeds?",
  "text_analysis":"is text readable at small size? too much or too little?",
  "face_emotion":"is there a face? does the emotion drive curiosity?",
  "improvements":["specific change 1","specific change 2","specific change 3","specific change 4"],
  "inspiration":"describe the ideal thumbnail for this type of video in detail"}}"""
    try:
        return jsonify(clean_json(groq_vision(b64, prompt, mime)))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 6. Title A/B tester
@app.route("/ab-test", methods=["POST"])
def ab_test():
    d = request.get_json()
    t1    = d.get("title1", "").strip()
    t2    = d.get("title2", "").strip()
    niche = d.get("niche", "").strip()
    if not t1 or not t2:
        return jsonify({"error": "Both titles are required."}), 400
    prompt = f"""YouTube CTR expert. Compare these two titles for a {niche} video.
Title A: {t1}
Title B: {t2}
Return ONLY raw JSON:
{{"winner":"A or B",
  "winner_reason":"why this title wins in 2 sentences",
  "title_a":{{"ctr_score":<0-100>,"emotional_hook":"<None|Weak|Medium|Strong>","curiosity_gap":"<None|Low|Medium|High>","keyword_strength":"<Weak|Medium|Strong>","length":"<Too Short|Good|Too Long>","improvements":["rewrite suggestion 1","rewrite suggestion 2"]}},
  "title_b":{{"ctr_score":<0-100>,"emotional_hook":"<None|Weak|Medium|Strong>","curiosity_gap":"<None|Low|Medium|High>","keyword_strength":"<Weak|Medium|Strong>","length":"<Too Short|Good|Too Long>","improvements":["rewrite suggestion 1","rewrite suggestion 2"]}},
  "best_alternative":"an even better title combining the best of both"}}"""
    try:
        return jsonify(clean_json(groq_chat(prompt, temp=0.4)))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 7. Content calendar
@app.route("/calendar", methods=["POST"])
def calendar():
    d = request.get_json()
    niche  = d.get("niche", "").strip()
    handle = d.get("handle", "").strip()
    freq   = d.get("frequency", "1 per day")
    lang   = d.get("language", "English")
    if not niche:
        return jsonify({"error": "Niche is required."}), 400
    prompt = f"""YouTube content strategist. Build a 30-day Shorts content calendar.
Channel:{handle} Niche:{niche} Posting:{freq} Language:{lang}
Return ONLY raw JSON:
{{"strategy_summary":"3 sentences explaining the 30-day growth strategy",
  "content_pillars":["pillar 1","pillar 2","pillar 3","pillar 4"],
  "week1":[{{"day":1,"title":"video title","hook":"first 2 seconds script","pillar":"which pillar","best_time":"e.g. 6pm IST"}},...7 items],
  "week2":[...same structure 7 items],
  "week3":[...7 items],
  "week4":[...9 items],
  "viral_ideas":["high-potential idea 1","idea 2","idea 3"],
  "series_concept":"a 5-part series concept that builds subscribers",
  "growth_tips":["week-specific tip 1","tip 2","tip 3","tip 4"]}}"""
    try:
        return jsonify(clean_json(groq_chat(prompt, temp=0.8, tokens=5000)))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 8. Trend detector
@app.route("/trends", methods=["POST"])
def trends():
    d = request.get_json()
    niche = d.get("niche", "").strip()
    geo   = d.get("geo", "India")
    if not niche:
        return jsonify({"error": "Niche is required."}), 400
    prompt = f"""YouTube trend analyst. Identify current content opportunities for {niche} in {geo}.
Return ONLY raw JSON:
{{"trending_formats":["format 1 with explanation","format 2",...5],
  "rising_topics":["topic 1","topic 2",...6],
  "avoid_topics":["oversaturated topic 1","topic 2",...3],
  "seasonal_opportunities":"upcoming festivals/events to create content around in next 30 days",
  "hashtag_trends":["#trend1","#trend2",...8],
  "competitor_moves":"what top creators in this niche are doing right now",
  "algorithm_tips":["what YouTube algorithm is favouring right now 1","tip 2",...4],
  "underserved_angles":["unique angle no one is covering 1","angle 2",...4]}}"""
    try:
        return jsonify(clean_json(groq_chat(prompt, temp=0.6)))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 9. Multi-language translate
@app.route("/translate", methods=["POST"])
def translate():
    d = request.get_json()
    description = d.get("description", "").strip()
    languages   = d.get("languages", [])
    if not description or not languages:
        return jsonify({"error": "Description and languages are required."}), 400
    langs_str = ", ".join(languages)
    # Build the JSON shape example without f-string brace confusion
    example_shape = '{"Telugu":"translated text","Tamil":"translated text",...}'
    prompt = f"""Translate this YouTube video description naturally (not literally) into: {langs_str}.
Keep hashtags, emojis, and the CTA intent intact. Adapt phrases to sound native.
Original:
{description}
Return ONLY raw JSON where keys are language names:
{example_shape}"""
    try:
        return jsonify(clean_json(groq_chat(prompt, temp=0.3, tokens=3000)))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── HTML ─────────────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>YouTube Growth Suite</title>
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet"/>
  <style>
    :root{--bg:#07070d;--s1:#111118;--s2:#18181f;--s3:#1f1f28;--bd:#2c2c3a;
          --red:#ff3535;--red2:#ff6b6b;--gold:#fbbf24;--green:#22c55e;
          --blue:#38bdf8;--purple:#a78bfa;--text:#e8e8f2;--muted:#7878a0;}
    *{box-sizing:border-box;margin:0;padding:0;}
    body{background:var(--bg);color:var(--text);font-family:"Space Grotesk",sans-serif;min-height:100vh;padding:28px 16px;}
    .glow{position:fixed;inset:0;z-index:0;
      background:radial-gradient(ellipse 60% 40% at 50% 0%,rgba(255,53,53,.07),transparent),
                 radial-gradient(ellipse 40% 30% at 80% 80%,rgba(56,189,248,.05),transparent);}
    .wrap{max-width:980px;margin:0 auto;position:relative;z-index:1;}
    header{text-align:center;margin-bottom:32px;}
    .logo{font-size:12px;font-family:"JetBrains Mono",monospace;color:var(--red);letter-spacing:4px;text-transform:uppercase;margin-bottom:10px;}
    h1{font-size:clamp(24px,4.5vw,44px);font-weight:700;line-height:1.1;}
    h1 em{color:var(--red);font-style:normal;}
    .sub{color:var(--muted);margin-top:8px;font-size:14px;}
    /* TABS */
    .tab-bar{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:24px;background:var(--s1);padding:5px;border-radius:14px;border:1px solid var(--bd);}
    .tab{flex:1;min-width:120px;padding:10px 8px;text-align:center;border-radius:10px;cursor:pointer;font-weight:600;font-size:13px;transition:all .2s;color:var(--muted);}
    .tab.on{background:var(--red);color:#fff;}
    .tab:hover:not(.on){background:var(--s2);color:var(--text);}
    .tc{display:none;} .tc.on{display:block;}
    /* CARDS */
    .card{background:var(--s1);border:1px solid var(--bd);border-radius:18px;padding:24px;margin-bottom:22px;}
    .card-title{font-size:11px;font-family:"JetBrains Mono",monospace;color:var(--red);letter-spacing:3px;text-transform:uppercase;margin-bottom:16px;}
    .grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
    .grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;}
    .span2{grid-column:1/-1;}
    label{display:block;font-size:11px;font-family:"JetBrains Mono",monospace;color:var(--muted);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:6px;}
    input,textarea,select{width:100%;padding:12px 14px;background:var(--s2);border:1px solid var(--bd);border-radius:11px;color:var(--text);font-family:"Space Grotesk",sans-serif;font-size:14px;transition:border-color .2s;outline:none;}
    input:focus,textarea:focus,select:focus{border-color:var(--red);}
    textarea{resize:vertical;}
    .hint{font-size:11px;color:var(--muted);margin-top:4px;font-family:"JetBrains Mono",monospace;}
    /* BUTTONS */
    .btn{display:flex;align-items:center;justify-content:center;gap:10px;width:100%;padding:14px;margin-top:18px;background:var(--red);color:#fff;border:none;border-radius:13px;font-size:15px;font-weight:700;font-family:"Space Grotesk",sans-serif;cursor:pointer;transition:all .2s;}
    .btn:hover{background:var(--red2);transform:translateY(-1px);}
    .btn:disabled{opacity:.5;cursor:not-allowed;transform:none;}
    .btn-ghost{background:var(--s2);border:1px solid var(--bd);color:var(--muted);}
    .btn-ghost:hover{border-color:var(--blue);color:var(--blue);background:var(--s2);}
    .spin{display:none;width:17px;height:17px;border:2.5px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:sp .7s linear infinite;}
    @keyframes sp{to{transform:rotate(360deg);}}
    /* RESULTS */
    .res{display:none;}
    .sec{background:var(--s1);border:1px solid var(--bd);border-radius:18px;padding:24px;margin-bottom:20px;}
    .sec-lbl{font-size:10px;font-family:"JetBrains Mono",monospace;color:var(--red);letter-spacing:3px;text-transform:uppercase;margin-bottom:14px;}
    .row-item{padding:10px 14px;background:var(--s2);border-radius:10px;margin-bottom:8px;border-left:3px solid var(--red);display:flex;justify-content:space-between;align-items:center;gap:12px;font-size:14px;}
    .cp{background:var(--bd);border:none;color:var(--muted);padding:5px 10px;border-radius:7px;cursor:pointer;font-size:11px;font-family:"JetBrains Mono",monospace;white-space:nowrap;transition:all .15s;}
    .cp:hover{background:var(--red);color:#fff;} .cp.ok{background:var(--green);color:#fff;}
    pre{font-family:"JetBrains Mono",monospace;font-size:13px;line-height:1.7;white-space:pre-wrap;color:var(--text);background:var(--s2);padding:16px;border-radius:12px;}
    .tags{display:flex;flex-wrap:wrap;gap:7px;}
    .tag{background:var(--s2);border:1px solid var(--bd);color:var(--red2);padding:5px 12px;border-radius:999px;font-size:12px;font-family:"JetBrains Mono",monospace;}
    .ideas-g{display:grid;grid-template-columns:1fr 1fr;gap:9px;}
    .idea{padding:10px 13px;background:var(--s2);border-radius:10px;font-size:13px;border-left:2px solid var(--gold);}
    .inum{color:var(--gold);font-weight:700;margin-right:5px;font-family:"JetBrains Mono",monospace;}
    .ck-item{display:flex;gap:9px;padding:8px 0;border-bottom:1px solid var(--bd);font-size:14px;}
    .ck-item:last-child{border:none;}
    .cki{color:var(--green);flex-shrink:0;}
    .cpa{display:flex;align-items:center;gap:6px;background:var(--s2);border:1px solid var(--bd);color:var(--muted);padding:6px 13px;border-radius:9px;cursor:pointer;font-size:11px;font-family:"JetBrains Mono",monospace;float:right;margin-bottom:10px;transition:all .15s;}
    .cpa:hover{border-color:var(--red);color:var(--red);}
    /* SCORE RING */
    .ring-wrap{display:flex;align-items:center;gap:20px;margin-bottom:18px;}
    .ring{width:84px;height:84px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:700;font-family:"JetBrains Mono",monospace;flex-shrink:0;}
    .ring.bad{background:rgba(255,53,53,.12);border:3px solid var(--red);color:var(--red);}
    .ring.ok{background:rgba(251,191,36,.1);border:3px solid var(--gold);color:var(--gold);}
    .ring.gd{background:rgba(34,197,94,.1);border:3px solid var(--green);color:var(--green);}
    .ring-info strong{display:block;font-size:17px;margin-bottom:4px;}
    .ring-info span{font-size:14px;color:var(--muted);}
    /* DIAG */
    .diag{padding:13px 15px;background:var(--s2);border-radius:11px;margin-bottom:9px;border-left:4px solid var(--red);}
    .diag.warn{border-color:var(--gold);} .diag.good{border-color:var(--green);}
    .diag-t{font-weight:700;font-size:14px;margin-bottom:3px;}
    .diag-b{font-size:13px;color:var(--muted);line-height:1.6;}
    /* FIX */
    .fix{padding:12px 15px;background:var(--s2);border-radius:11px;margin-bottom:8px;display:flex;gap:11px;align-items:flex-start;}
    .fnum{background:var(--red);color:#fff;width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;flex-shrink:0;}
    .ftxt strong{display:block;font-size:14px;margin-bottom:2px;}
    .ftxt span{font-size:13px;color:var(--muted);}
    /* OPP */
    .opp{padding:12px 15px;background:var(--s2);border-radius:11px;margin-bottom:8px;border-left:3px solid var(--blue);}
    .opp-t{font-weight:700;font-size:14px;color:var(--blue);margin-bottom:3px;}
    .opp-b{font-size:13px;color:var(--muted);line-height:1.6;}
    /* CHANNEL CARD */
    .ch-card{background:var(--s2);border:1px solid var(--bd);border-radius:14px;padding:18px;margin-bottom:14px;}
    .ch-stat{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:12px;}
    .stat-box{background:var(--s3);border-radius:10px;padding:12px;text-align:center;}
    .stat-n{font-size:20px;font-weight:700;color:var(--red);}
    .stat-l{font-size:11px;color:var(--muted);margin-top:2px;}
    /* THUMBNAIL */
    .grade{font-size:42px;font-weight:700;font-family:"JetBrains Mono",monospace;}
    .grade.A{color:var(--green);} .grade.B{color:#86efac;} .grade.C{color:var(--gold);} .grade.D,.grade.F{color:var(--red);}
    .str{padding:10px 14px;background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.2);border-radius:10px;margin-bottom:8px;font-size:14px;}
    .wk{padding:10px 14px;background:rgba(255,53,53,.08);border:1px solid rgba(255,53,53,.2);border-radius:10px;margin-bottom:8px;font-size:14px;}
    .str-t{color:var(--green);font-weight:700;} .wk-t{color:var(--red);font-weight:700;}
    /* AB */
    .ab-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:6px;}
    .ab-card{background:var(--s2);border:1px solid var(--bd);border-radius:13px;padding:16px;}
    .ab-card.winner{border-color:var(--green);}
    .ab-score{font-size:28px;font-weight:700;font-family:"JetBrains Mono",monospace;color:var(--red);}
    .ab-score.win{color:var(--green);}
    .ab-meta{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0;}
    .pill{padding:4px 10px;border-radius:999px;font-size:11px;font-family:"JetBrains Mono",monospace;background:var(--s3);border:1px solid var(--bd);}
    /* CALENDAR */
    .cal-day{padding:11px 14px;background:var(--s2);border-radius:10px;margin-bottom:7px;border-left:3px solid var(--purple);}
    .cal-day-n{font-size:11px;font-family:"JetBrains Mono",monospace;color:var(--purple);margin-bottom:3px;}
    .cal-title{font-size:14px;font-weight:600;margin-bottom:2px;}
    .cal-meta{font-size:12px;color:var(--muted);}
    /* TREND */
    .trend-item{padding:10px 14px;background:var(--s2);border-radius:10px;margin-bottom:7px;border-left:2px solid var(--gold);font-size:14px;}
    /* ERROR */
    .err{background:rgba(255,53,53,.1);border:1px solid rgba(255,53,53,.3);color:var(--red2);padding:12px;border-radius:11px;display:none;margin-top:12px;font-size:14px;}
    /* UPLOAD */
    .upload-zone{border:2px dashed var(--bd);border-radius:13px;padding:30px;text-align:center;cursor:pointer;transition:all .2s;color:var(--muted);}
    .upload-zone:hover{border-color:var(--red);color:var(--text);}
    .upload-zone.has-file{border-color:var(--green);color:var(--green);}
    #thumb-preview{max-width:100%;max-height:220px;border-radius:10px;margin-top:12px;display:none;}
    /* LANG CHIPS */
    .lang-chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px;}
    .lang-chip{padding:8px 14px;border-radius:999px;border:1px solid var(--bd);cursor:pointer;font-size:13px;transition:all .2s;background:var(--s2);}
    .lang-chip.sel{background:var(--red);border-color:var(--red);color:#fff;}
    @media(max-width:640px){.grid2,.grid3,.ideas-g,.ab-grid,.ch-stat{grid-template-columns:1fr!important;}.tab{min-width:80px;font-size:12px;}}
  </style>
</head>
<body>
<div class="glow"></div>
<div class="wrap">
  <header>
    <div class="logo">// YouTube Growth Suite v3</div>
    <h1>All-in-One <em>YouTube</em> Growth Tool</h1>
    <p class="sub">SEO • Analytics • Competitor Intel • Thumbnail AI • Calendar • Trends — powered by Groq</p>
  </header>

  <div class="tab-bar">
    <div class="tab on"  onclick="sw(0)">🚀 SEO</div>
    <div class="tab"     onclick="sw(1)">📊 Analytics</div>
    <div class="tab"     onclick="sw(2)">🔍 Competitor</div>
    <div class="tab"     onclick="sw(3)">🖼️ Thumbnail</div>
    <div class="tab"     onclick="sw(4)">📅 Calendar</div>
    <div class="tab"     onclick="sw(5)">🌏 Trends & Translate</div>
  </div>

  <!-- ══ TAB 0: SEO ══ -->
  <div class="tc on" id="t0">
    <div class="card">
      <div class="card-title">SEO Content Generator</div>
      <div class="grid2">
        <div><label>YouTube Handle</label><input id="s_handle" placeholder="@YourChannel"/></div>
        <div><label>Video / Shorts URL</label><input id="s_url" placeholder="https://youtube.com/shorts/..."/></div>
        <div><label>Topic / Niche</label><input id="s_topic" placeholder="e.g. Telugu comedy"/></div>
        <div><label>Target Keywords</label><input id="s_kw" placeholder="e.g. telugu shorts, funny, viral"/></div>
      </div>
      <div class="err" id="e0"></div>
      <button class="btn" id="b0" onclick="genSEO()"><span id="b0t">🚀 Generate SEO Plan</span><div class="spin" id="b0s"></div></button>
    </div>
    <div class="res" id="r0">
      <div class="sec"><div class="sec-lbl">▸ SEO Titles</div><div id="titlesOut"></div></div>
      <div class="sec"><div class="sec-lbl">▸ Description</div><button class="cpa" onclick="cpEl('descOut')">📋 Copy</button><pre id="descOut"></pre></div>
      <div class="sec"><div class="sec-lbl">▸ Hashtags</div><div class="tags" id="tagsOut"></div></div>
      <div class="sec"><div class="sec-lbl">▸ Pinned Comment</div><button class="cpa" onclick="cpEl('pinnedOut')">📋 Copy</button><pre id="pinnedOut"></pre></div>
      <div class="sec"><div class="sec-lbl">▸ 30 Shorts Ideas</div><div class="ideas-g" id="ideasOut"></div></div>
      <div class="sec"><div class="sec-lbl">▸ Upload Checklist</div><div id="ckOut"></div></div>
    </div>
  </div>

  <!-- ══ TAB 1: ANALYTICS ══ -->
  <div class="tc" id="t1">
    <div class="card">
      <div class="card-title">⚡ Auto-Fetch Channel Stats (YouTube API)</div>
      <p class="hint" style="margin-bottom:14px;">Enter your YouTube Data API v3 key to auto-fill stats from your channel.</p>
      <div class="grid2">
        <div><label>YouTube Handle</label><input id="af_handle" placeholder="@YourChannel"/></div>
        <div><label>YouTube API Key</label><input id="af_key" type="password" placeholder="AIza..."/></div>
      </div>
      <div class="err" id="eaf"></div>
      <button class="btn btn-ghost" id="baf" onclick="autoFetch()"><span id="baft">⚡ Auto-Fetch My Stats</span><div class="spin" id="bafs"></div></button>
      <div id="fetchedCard" style="display:none;margin-top:16px;"></div>
    </div>
    <div class="card">
      <div class="card-title">Manual Analytics Input</div>
      <p class="hint" style="margin-bottom:14px;">Go to YouTube Studio → Analytics and paste your numbers below.</p>
      <div class="grid2">
        <div><label>Channel Handle</label><input id="a_handle" placeholder="@YourChannel"/></div>
        <div><label>Niche / Topic</label><input id="a_niche" placeholder="e.g. Telugu comedy Shorts"/></div>
        <div><label>Channel Age</label>
          <select id="a_age"><option value="">Select...</option><option>Less than 1 month</option><option>1–3 months</option><option>3–6 months</option><option>6–12 months</option><option>1–2 years</option><option>2+ years</option></select>
        </div>
        <div><label>Total Videos Posted</label><input id="a_tvid" type="number" placeholder="45"/></div>
      </div>
      <p class="hint" style="margin:16px 0 10px;">Last 28 Days</p>
      <div class="grid3">
        <div class="stat-box"><label>Views</label><input id="a_views" type="number" placeholder="1200"/></div>
        <div class="stat-box"><label>Impressions</label><input id="a_imp" type="number" placeholder="8000"/></div>
        <div class="stat-box"><label>CTR %</label><input id="a_ctr" type="number" step="0.1" placeholder="4.2"/></div>
        <div class="stat-box"><label>Watch Time (hrs)</label><input id="a_wt" type="number" placeholder="320"/></div>
        <div class="stat-box"><label>Avg Duration (sec)</label><input id="a_avd" type="number" placeholder="45"/></div>
        <div class="stat-box"><label>New Subscribers</label><input id="a_ns" type="number" placeholder="38"/></div>
        <div class="stat-box"><label>Total Subs</label><input id="a_ts" type="number" placeholder="420"/></div>
        <div class="stat-box"><label>Likes</label><input id="a_lk" type="number" placeholder="95"/></div>
        <div class="stat-box"><label>Comments</label><input id="a_cm" type="number" placeholder="12"/></div>
      </div>
      <div class="grid2" style="margin-top:12px;">
        <div class="span2"><label>Top 3 Videos (title + views)</label><textarea id="a_tv" rows="3" placeholder="1. Village comedy — 4,200 views&#10;2. Market prank — 2,800 views"></textarea></div>
        <div><label>Traffic Sources</label><input id="a_tr" placeholder="Search 40%, Suggested 30%..."/></div>
        <div><label>Audience Geography</label><input id="a_geo" placeholder="India 85%, USA 5%..."/></div>
      </div>
      <div class="err" id="e1"></div>
      <button class="btn" id="b1" onclick="genAnalytics()"><span id="b1t">📊 Analyse My Channel</span><div class="spin" id="b1s"></div></button>
    </div>
    <div class="res" id="r1">
      <div class="sec"><div class="sec-lbl">▸ Channel Health</div><div id="scoreOut"></div></div>
      <div class="sec"><div class="sec-lbl">▸ What's Holding You Back</div><div id="diagOut"></div></div>
      <div class="sec"><div class="sec-lbl">▸ Fix Plan</div><div id="fixOut"></div></div>
      <div class="sec"><div class="sec-lbl">▸ Growth Opportunities</div><div id="oppOut"></div></div>
      <div class="sec"><div class="sec-lbl">▸ Best Times To Post</div><pre id="timeOut"></pre></div>
      <div class="sec"><div class="sec-lbl">▸ 30-Day Roadmap</div><pre id="roadOut"></pre></div>
    </div>
  </div>

  <!-- ══ TAB 2: COMPETITOR ══ -->
  <div class="tc" id="t2">
    <div class="card">
      <div class="card-title">Competitor Intelligence</div>
      <div class="grid2">
        <div><label>Competitor Handle</label><input id="c_handle" placeholder="@CompetitorChannel"/></div>
        <div><label>YouTube API Key</label><input id="c_key" type="password" placeholder="AIza..."/></div>
        <div class="span2"><label>Your Niche</label><input id="c_niche" placeholder="e.g. Telugu comedy Shorts"/></div>
      </div>
      <div class="err" id="e2"></div>
      <button class="btn" id="b2" onclick="genCompetitor()"><span id="b2t">🔍 Analyse Competitor</span><div class="spin" id="b2s"></div></button>
    </div>
    <div class="res" id="r2">
      <div class="sec"><div class="sec-lbl">▸ Their Strengths</div><div id="cStrOut"></div></div>
      <div class="sec"><div class="sec-lbl">▸ Their Weaknesses</div><div id="cWkOut"></div></div>
      <div class="sec"><div class="sec-lbl">▸ Content Gaps You Can Own</div><div id="cGapOut"></div></div>
      <div class="sec"><div class="sec-lbl">▸ Ideas To Steal & Do Better</div><div id="cStealOut"></div></div>
      <div class="sec"><div class="sec-lbl">▸ Thumbnail & Posting Patterns</div><pre id="cPatOut"></pre></div>
      <div class="sec"><div class="sec-lbl">▸ Action Plan To Outrank Them</div><div id="cActOut"></div></div>
    </div>
  </div>

  <!-- ══ TAB 3: THUMBNAIL ══ -->
  <div class="tc" id="t3">
    <div class="card">
      <div class="card-title">🖼️ Thumbnail AI Scorer</div>
      <div><label>Your Niche</label><input id="th_niche" placeholder="e.g. Telugu comedy Shorts" style="margin-bottom:14px;"/></div>
      <div class="upload-zone" id="dropZone" onclick="document.getElementById('th_img').click()">
        <div style="font-size:28px;margin-bottom:8px;">📸</div>
        <div style="font-weight:600;">Click to upload thumbnail</div>
        <div class="hint" style="margin-top:4px;">JPG, PNG, WEBP — max 5MB</div>
        <img id="thumb-preview"/>
      </div>
      <input type="file" id="th_img" accept="image/*" style="display:none" onchange="previewThumb(this)"/>
      <div class="err" id="e3"></div>
      <button class="btn" id="b3" onclick="genThumb()"><span id="b3t">🎯 Score My Thumbnail</span><div class="spin" id="b3s"></div></button>
    </div>
    <div class="card" style="margin-top:0;">
      <div class="card-title">🔤 Title A/B Tester</div>
      <div class="grid2">
        <div><label>Title A</label><input id="ab_t1" placeholder="Your first title idea"/></div>
        <div><label>Title B</label><input id="ab_t2" placeholder="Your second title idea"/></div>
        <div class="span2"><label>Niche</label><input id="ab_niche" placeholder="e.g. Telugu comedy"/></div>
      </div>
      <div class="err" id="e3b"></div>
      <button class="btn btn-ghost" id="b3b" onclick="genAB()"><span id="b3bt">⚔️ Compare Titles</span><div class="spin" id="b3bs"></div></button>
    </div>
    <div class="res" id="r3">
      <div class="sec"><div class="sec-lbl">▸ Thumbnail Score</div><div id="thScoreOut"></div></div>
      <div class="sec"><div class="sec-lbl">▸ Strengths</div><div id="thStrOut"></div></div>
      <div class="sec"><div class="sec-lbl">▸ Weaknesses</div><div id="thWkOut"></div></div>
      <div class="sec"><div class="sec-lbl">▸ Improvements</div><div id="thImpOut"></div></div>
      <div class="sec"><div class="sec-lbl">▸ Ideal Thumbnail Description</div><pre id="thInsOut"></pre></div>
    </div>
    <div class="res" id="r3b">
      <div class="sec"><div class="sec-lbl">▸ A/B Test Result</div><div id="abOut"></div></div>
    </div>
  </div>

  <!-- ══ TAB 4: CALENDAR ══ -->
  <div class="tc" id="t4">
    <div class="card">
      <div class="card-title">30-Day Content Calendar</div>
      <div class="grid2">
        <div><label>Channel Handle</label><input id="cl_handle" placeholder="@YourChannel"/></div>
        <div><label>Niche / Topic</label><input id="cl_niche" placeholder="e.g. Telugu comedy Shorts"/></div>
        <div><label>Posting Frequency</label>
          <select id="cl_freq">
            <option>1 video per day</option><option>2 videos per day</option>
            <option>1 video every 2 days</option><option>3 videos per week</option>
          </select>
        </div>
        <div><label>Primary Language</label>
          <select id="cl_lang">
            <option>English</option><option>Telugu</option><option>Tamil</option>
            <option>Hindi</option><option>Kannada</option><option>Malayalam</option>
          </select>
        </div>
      </div>
      <div class="err" id="e4"></div>
      <button class="btn" id="b4" onclick="genCalendar()"><span id="b4t">📅 Build My Calendar</span><div class="spin" id="b4s"></div></button>
    </div>
    <div class="res" id="r4">
      <div class="sec"><div class="sec-lbl">▸ Strategy</div><pre id="calStratOut"></pre></div>
      <div class="sec"><div class="sec-lbl">▸ Content Pillars</div><div id="calPillarOut"></div></div>
      <div class="sec"><div class="sec-lbl">▸ Week 1</div><div id="calW1Out"></div></div>
      <div class="sec"><div class="sec-lbl">▸ Week 2</div><div id="calW2Out"></div></div>
      <div class="sec"><div class="sec-lbl">▸ Week 3</div><div id="calW3Out"></div></div>
      <div class="sec"><div class="sec-lbl">▸ Week 4</div><div id="calW4Out"></div></div>
      <div class="sec"><div class="sec-lbl">▸ Viral Ideas & Series Concept</div><pre id="calViralOut"></pre></div>
    </div>
  </div>

  <!-- ══ TAB 5: TRENDS & TRANSLATE ══ -->
  <div class="tc" id="t5">
    <div class="card">
      <div class="card-title">📈 Trend Detector</div>
      <div class="grid2">
        <div><label>Niche / Topic</label><input id="tr_niche" placeholder="e.g. Telugu comedy Shorts"/></div>
        <div><label>Target Region</label>
          <select id="tr_geo">
            <option>India</option><option>Andhra Pradesh / Telangana</option>
            <option>Tamil Nadu</option><option>Karnataka</option>
            <option>Global</option><option>USA</option>
          </select>
        </div>
      </div>
      <div class="err" id="e5a"></div>
      <button class="btn" id="b5a" onclick="genTrends()"><span id="b5at">📈 Detect Trends</span><div class="spin" id="b5as"></div></button>
    </div>
    <div class="res" id="r5a">
      <div class="sec"><div class="sec-lbl">▸ Trending Formats</div><div id="trFmtOut"></div></div>
      <div class="sec"><div class="sec-lbl">▸ Rising Topics to Cover</div><div id="trTopOut"></div></div>
      <div class="sec"><div class="sec-lbl">▸ Trending Hashtags</div><div class="tags" id="trTagOut"></div></div>
      <div class="sec"><div class="sec-lbl">▸ Seasonal Opportunities</div><pre id="trSeaOut"></pre></div>
      <div class="sec"><div class="sec-lbl">▸ Underserved Angles</div><div id="trAngOut"></div></div>
      <div class="sec"><div class="sec-lbl">▸ Algorithm Tips Right Now</div><div id="trAlgOut"></div></div>
    </div>
    <div class="card" style="margin-top:4px;">
      <div class="card-title">🌏 Multi-Language Description</div>
      <div><label>Video Description (English)</label>
        <textarea id="tl_desc" rows="5" placeholder="Paste your English description here..."></textarea>
      </div>
      <label style="margin-top:14px;">Translate To</label>
      <div class="lang-chips" id="langChips">
        <div class="lang-chip sel" data-lang="Telugu">Telugu</div>
        <div class="lang-chip sel" data-lang="Tamil">Tamil</div>
        <div class="lang-chip" data-lang="Hindi">Hindi</div>
        <div class="lang-chip" data-lang="Kannada">Kannada</div>
        <div class="lang-chip" data-lang="Malayalam">Malayalam</div>
        <div class="lang-chip" data-lang="Bengali">Bengali</div>
        <div class="lang-chip" data-lang="Marathi">Marathi</div>
      </div>
      <div class="err" id="e5b"></div>
      <button class="btn btn-ghost" id="b5b" onclick="genTranslate()"><span id="b5bt">🌏 Translate Description</span><div class="spin" id="b5bs"></div></button>
    </div>
    <div class="res" id="r5b">
      <div class="sec"><div class="sec-lbl">▸ Translated Descriptions</div><div id="tlOut"></div></div>
    </div>
  </div>
</div>

<script>
const $ = id => document.getElementById(id);
const val = id => $(id).value.trim();

function sw(i){
  document.querySelectorAll(".tab").forEach((t,j)=>t.classList.toggle("on",j===i));
  document.querySelectorAll(".tc").forEach((t,j)=>t.classList.toggle("on",j===i));
}
function ld(bid,tid,sid,on,label){
  $(bid).disabled=on; $(tid).textContent=label; $(sid).style.display=on?"block":"none";
}
function show(id){const e=$(id);e.style.display="block";e.scrollIntoView({behavior:"smooth"});}
async function api(url,body){
  const r=await fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
  const d=await r.json(); if(d.error)throw new Error(d.error); return d;
}
function cpEl(id){navigator.clipboard.writeText($(id).textContent);}
function cpStr(btn,txt){
  navigator.clipboard.writeText(txt);
  btn.textContent="Copied!";btn.classList.add("ok");
  setTimeout(()=>{btn.textContent="Copy";btn.classList.remove("ok");},2000);
}
function esc(s){return s.replace(/\\/g,"\\\\").replace(/'/g,"\\'").replace(/"/g,"&quot;");}
function fmt(n){
  if(n>=1000000)return(n/1000000).toFixed(1)+"M";
  if(n>=1000)return(n/1000).toFixed(1)+"K";
  return String(n);
}

function previewThumb(inp){
  const f=inp.files[0]; if(!f)return;
  const rdr=new FileReader();
  rdr.onload=e=>{
    $("thumb-preview").src=e.target.result;
    $("thumb-preview").style.display="block";
    $("dropZone").classList.add("has-file");
  };
  rdr.readAsDataURL(f);
}

document.querySelectorAll(".lang-chip").forEach(c=>{
  c.addEventListener("click",()=>c.classList.toggle("sel"));
});

// ══ TAB 0: SEO ══
async function genSEO(){
  $("e0").style.display="none";
  const handle=val("s_handle"),url=val("s_url"),topic=val("s_topic"),keywords=val("s_kw");
  if(!handle||!url||!topic){$("e0").textContent="Handle, URL and Topic required.";$("e0").style.display="block";return;}
  ld("b0","b0t","b0s",true,"Generating...");$("r0").style.display="none";
  try{
    const d=await api("/generate",{handle,url,topic,keywords});
    $("titlesOut").innerHTML=(d.titles||[]).map(t=>`<div class="row-item"><span>${t}</span><button class="cp" onclick="cpStr(this,'${esc(t)}')">Copy</button></div>`).join("");
    $("descOut").textContent=d.description||"";
    $("tagsOut").innerHTML=(d.hashtags||[]).map(h=>`<span class="tag">${h}</span>`).join("");
    $("pinnedOut").textContent=d.pinned_comment||"";
    $("ideasOut").innerHTML=(d.ideas||[]).map((x,i)=>`<div class="idea"><span class="inum">${i+1}.</span>${x}</div>`).join("");
    $("ckOut").innerHTML=(d.checklist||[]).map(x=>`<div class="ck-item"><span class="cki">✓</span><span>${x}</span></div>`).join("");
    show("r0");
  }catch(e){$("e0").textContent="Error: "+e.message;$("e0").style.display="block";}
  finally{ld("b0","b0t","b0s",false,"🚀 Generate SEO Plan");}
}

// ══ AUTO FETCH ══
async function autoFetch(){
  $("eaf").style.display="none";
  const handle=val("af_handle"),yt_key=val("af_key");
  if(!handle||!yt_key){$("eaf").textContent="Handle and API Key required.";$("eaf").style.display="block";return;}
  ld("baf","baft","bafs",true,"Fetching...");$("fetchedCard").style.display="none";
  try{
    const d=await api("/fetch-channel",{handle,yt_key});
    $("fetchedCard").innerHTML=`
      <div class="ch-card">
        <strong style="font-size:16px;">${d.name}</strong>
        <p style="color:var(--muted);font-size:13px;margin-top:4px;">${d.description||""}</p>
        <div class="ch-stat">
          <div class="stat-box"><div class="stat-n">${fmt(d.subscribers)}</div><div class="stat-l">Subscribers</div></div>
          <div class="stat-box"><div class="stat-n">${fmt(d.total_views)}</div><div class="stat-l">Total Views</div></div>
          <div class="stat-box"><div class="stat-n">${fmt(d.video_count)}</div><div class="stat-l">Videos</div></div>
          <div class="stat-box"><div class="stat-n">${d.country||"N/A"}</div><div class="stat-l">Country</div></div>
        </div>
        ${d.top_videos&&d.top_videos.length?`<p style="font-size:11px;color:var(--muted);margin-top:14px;font-family:'JetBrains Mono',monospace;text-transform:uppercase;letter-spacing:2px;">Top Videos</p>
        ${d.top_videos.map(vid=>`<div class="row-item" style="margin-top:7px;">${vid.title}<span style="color:var(--muted);font-size:12px;flex-shrink:0;">${fmt(vid.views)} views</span></div>`).join("")}`:""}
      </div>`;
    $("fetchedCard").style.display="block";
    $("a_handle").value=handle;
    $("a_ts").value=d.subscribers;
    $("a_tvid").value=d.video_count;
  }catch(e){$("eaf").textContent="Error: "+e.message;$("eaf").style.display="block";}
  finally{ld("baf","baft","bafs",false,"⚡ Auto-Fetch My Stats");}
}

// ══ TAB 1: ANALYTICS ══
async function genAnalytics(){
  $("e1").style.display="none";
  const payload={
    handle:val("a_handle"),niche:val("a_niche"),age:val("a_age"),total_videos:val("a_tvid"),
    views:val("a_views"),impressions:val("a_imp"),ctr:val("a_ctr"),watchtime:val("a_wt"),
    avd:val("a_avd"),subs:val("a_ns"),total_subs:val("a_ts"),likes:val("a_lk"),comments:val("a_cm"),
    top_videos:val("a_tv"),traffic:val("a_tr"),geo:val("a_geo")
  };
  if(!payload.niche||!payload.views){$("e1").textContent="Niche and Views are required.";$("e1").style.display="block";return;}
  ld("b1","b1t","b1s",true,"Analysing...");$("r1").style.display="none";
  try{
    const d=await api("/analyse",payload);
    const sc=d.score||0, cls=sc<40?"bad":sc<70?"ok":"gd";
    $("scoreOut").innerHTML=`<div class="ring-wrap"><div class="ring ${cls}">${sc}</div><div class="ring-info"><strong>${d.score_label||""}</strong><span>${d.score_summary||""}</span></div></div>`;
    $("diagOut").innerHTML=(d.diagnosis||[]).map(x=>`<div class="diag ${x.severity==="warning"?"warn":x.severity==="ok"?"good":""}"><div class="diag-t">${x.severity==="ok"?"✅":"❌"} ${x.title}</div><div class="diag-b">${x.detail}</div></div>`).join("");
    $("fixOut").innerHTML=(d.fixes||[]).map((f,i)=>`<div class="fix"><div class="fnum">${i+1}</div><div class="ftxt"><strong>${f.action}</strong><span>${f.detail}</span></div></div>`).join("");
    $("oppOut").innerHTML=(d.opportunities||[]).map(o=>`<div class="opp"><div class="opp-t">💡 ${o.title}</div><div class="opp-b">${o.detail}</div></div>`).join("");
    $("timeOut").textContent=d.best_post_times||"";
    $("roadOut").textContent=d.roadmap||"";
    show("r1");
  }catch(e){$("e1").textContent="Error: "+e.message;$("e1").style.display="block";}
  finally{ld("b1","b1t","b1s",false,"📊 Analyse My Channel");}
}

// ══ TAB 2: COMPETITOR ══
async function genCompetitor(){
  $("e2").style.display="none";
  const handle=val("c_handle"),yt_key=val("c_key"),my_niche=val("c_niche");
  if(!handle||!yt_key){$("e2").textContent="Competitor handle and API Key required.";$("e2").style.display="block";return;}
  ld("b2","b2t","b2s",true,"Analysing...");$("r2").style.display="none";
  try{
    const d=await api("/competitor",{handle,yt_key,my_niche});
    const mkList=(arr,color="var(--text)")=>arr.map(x=>`<div class="trend-item" style="border-color:${color};">${x}</div>`).join("");
    $("cStrOut").innerHTML=mkList(d.competitor_strengths||[],"var(--green)");
    $("cWkOut").innerHTML=mkList(d.competitor_weaknesses||[],"var(--red)");
    $("cGapOut").innerHTML=mkList(d.content_gaps||[],"var(--blue)");
    $("cStealOut").innerHTML=mkList(d.steal_these_ideas||[],"var(--gold)");
    $("cPatOut").textContent=`Thumbnails: ${d.thumbnail_patterns||""}\n\nPosting: ${d.posting_frequency||""}`;
    $("cActOut").innerHTML=(d.action_plan||[]).map((a,i)=>`<div class="fix"><div class="fnum">${i+1}</div><div class="ftxt"><strong>${a}</strong></div></div>`).join("");
    show("r2");
  }catch(e){$("e2").textContent="Error: "+e.message;$("e2").style.display="block";}
  finally{ld("b2","b2t","b2s",false,"🔍 Analyse Competitor");}
}

// ══ TAB 3: THUMBNAIL ══
async function genThumb(){
  $("e3").style.display="none";
  const img=$("th_img").files[0], niche=val("th_niche");
  if(!img){$("e3").textContent="Please upload a thumbnail image.";$("e3").style.display="block";return;}
  ld("b3","b3t","b3s",true,"Scoring...");$("r3").style.display="none";
  try{
    const fd=new FormData(); fd.append("image",img); fd.append("niche",niche);
    const r=await fetch("/thumbnail",{method:"POST",body:fd});
    const d=await r.json(); if(d.error)throw new Error(d.error);
    $("thScoreOut").innerHTML=`<div class="ring-wrap"><div class="grade ${d.grade||"C"}">${d.grade||"?"}</div><div class="ring-info"><strong>Score: ${d.score||0}/100</strong><span>${d.summary||""}</span><br><span style="color:var(--muted);font-size:12px;">CTR Prediction: ${d.ctr_prediction||""}</span></div></div>`;
    $("thStrOut").innerHTML=(d.strengths||[]).map(s=>`<div class="str"><span class="str-t">✅ ${s.point}</span><br><span style="color:var(--muted);font-size:13px;">${s.detail}</span></div>`).join("");
    $("thWkOut").innerHTML=(d.weaknesses||[]).map(w=>`<div class="wk"><span class="wk-t">⚠️ ${w.point}</span><br><span style="color:var(--muted);font-size:13px;">${w.detail}</span></div>`).join("");
    $("thImpOut").innerHTML=(d.improvements||[]).map((x,i)=>`<div class="fix"><div class="fnum">${i+1}</div><div class="ftxt"><strong>${x}</strong></div></div>`).join("");
    $("thInsOut").textContent=`Color Analysis:\n${d.color_analysis||""}\n\nText Analysis:\n${d.text_analysis||""}\n\nFace/Emotion:\n${d.face_emotion||""}\n\nIdeal Thumbnail:\n${d.inspiration||""}`;
    show("r3");
  }catch(e){$("e3").textContent="Error: "+e.message;$("e3").style.display="block";}
  finally{ld("b3","b3t","b3s",false,"🎯 Score My Thumbnail");}
}

// ══ A/B TEST ══
async function genAB(){
  $("e3b").style.display="none";
  const title1=val("ab_t1"),title2=val("ab_t2"),niche=val("ab_niche");
  if(!title1||!title2){$("e3b").textContent="Both titles required.";$("e3b").style.display="block";return;}
  ld("b3b","b3bt","b3bs",true,"Comparing...");$("r3b").style.display="none";
  try{
    const d=await api("/ab-test",{title1,title2,niche});
    const mkCard=(label,data,won)=>`
      <div class="ab-card ${won?"winner":""}">
        <div style="font-size:12px;color:var(--muted);margin-bottom:6px;">TITLE ${label} ${won?"👑":""}</div>
        <div style="font-size:15px;font-weight:600;margin-bottom:10px;">${label==="A"?title1:title2}</div>
        <div class="ab-score ${won?"win":""}">${data.ctr_score||0}</div>
        <div style="font-size:11px;color:var(--muted);">CTR Score</div>
        <div class="ab-meta">
          <span class="pill">Hook: ${data.emotional_hook}</span>
          <span class="pill">Curiosity: ${data.curiosity_gap}</span>
          <span class="pill">SEO: ${data.keyword_strength}</span>
          <span class="pill">Length: ${data.length}</span>
        </div>
        <div style="font-size:12px;color:var(--muted);">Suggestions:</div>
        ${(data.improvements||[]).map(x=>`<div style="font-size:13px;padding:4px 0;color:var(--text);">→ ${x}</div>`).join("")}
      </div>`;
    $("abOut").innerHTML=`
      <div style="padding:14px;background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.25);border-radius:12px;margin-bottom:16px;">
        <strong style="color:var(--green);">🏆 Winner: Title ${d.winner}</strong><br>
        <span style="font-size:14px;color:var(--muted);">${d.winner_reason||""}</span>
      </div>
      <div class="ab-grid">
        ${mkCard("A",d.title_a||{},d.winner==="A")}
        ${mkCard("B",d.title_b||{},d.winner==="B")}
      </div>
      <div style="margin-top:16px;padding:14px;background:var(--s2);border-radius:12px;border-left:3px solid var(--gold);">
        <div style="font-size:11px;color:var(--gold);font-family:'JetBrains Mono',monospace;margin-bottom:6px;">💡 EVEN BETTER ALTERNATIVE</div>
        <div style="font-size:15px;font-weight:600;">${d.best_alternative||""}</div>
      </div>`;
    show("r3b");
  }catch(e){$("e3b").textContent="Error: "+e.message;$("e3b").style.display="block";}
  finally{ld("b3b","b3bt","b3bs",false,"⚔️ Compare Titles");}
}

// ══ TAB 4: CALENDAR ══
async function genCalendar(){
  $("e4").style.display="none";
  const niche=val("cl_niche");
  if(!niche){$("e4").textContent="Niche is required.";$("e4").style.display="block";return;}
  ld("b4","b4t","b4s",true,"Building...");$("r4").style.display="none";
  try{
    const d=await api("/calendar",{handle:val("cl_handle"),niche,frequency:val("cl_freq"),language:val("cl_lang")});
    $("calStratOut").textContent=d.strategy_summary||"";
    $("calPillarOut").innerHTML=(d.content_pillars||[]).map(p=>`<div class="trend-item" style="border-color:var(--purple);">📌 ${p}</div>`).join("");
    const mkWeek=days=>(days||[]).map(entry=>`<div class="cal-day"><div class="cal-day-n">Day ${entry.day} · ${entry.best_time||""}</div><div class="cal-title">${entry.title}</div><div class="cal-meta">🎯 ${entry.pillar||""} &nbsp;|&nbsp; Hook: ${entry.hook||""}</div></div>`).join("");
    $("calW1Out").innerHTML=mkWeek(d.week1);
    $("calW2Out").innerHTML=mkWeek(d.week2);
    $("calW3Out").innerHTML=mkWeek(d.week3);
    $("calW4Out").innerHTML=mkWeek(d.week4);
    $("calViralOut").textContent=`Viral Ideas:\n${(d.viral_ideas||[]).map((x,i)=>`${i+1}. ${x}`).join("\n")}\n\nSeries Concept:\n${d.series_concept||""}`;
    show("r4");
  }catch(e){$("e4").textContent="Error: "+e.message;$("e4").style.display="block";}
  finally{ld("b4","b4t","b4s",false,"📅 Build My Calendar");}
}

// ══ TAB 5: TRENDS ══
async function genTrends(){
  $("e5a").style.display="none";
  const niche=val("tr_niche"),geo=val("tr_geo");
  if(!niche){$("e5a").textContent="Niche required.";$("e5a").style.display="block";return;}
  ld("b5a","b5at","b5as",true,"Detecting...");$("r5a").style.display="none";
  try{
    const d=await api("/trends",{niche,geo});
    $("trFmtOut").innerHTML=(d.trending_formats||[]).map(x=>`<div class="trend-item">${x}</div>`).join("");
    $("trTopOut").innerHTML=(d.rising_topics||[]).map(x=>`<div class="trend-item" style="border-color:var(--blue);">${x}</div>`).join("");
    $("trTagOut").innerHTML=(d.hashtag_trends||[]).map(h=>`<span class="tag">${h}</span>`).join("");
    $("trSeaOut").textContent=d.seasonal_opportunities||"";
    $("trAngOut").innerHTML=(d.underserved_angles||[]).map(x=>`<div class="trend-item" style="border-color:var(--purple);">💡 ${x}</div>`).join("");
    $("trAlgOut").innerHTML=(d.algorithm_tips||[]).map(x=>`<div class="trend-item" style="border-color:var(--green);">⚡ ${x}</div>`).join("");
    show("r5a");
  }catch(e){$("e5a").textContent="Error: "+e.message;$("e5a").style.display="block";}
  finally{ld("b5a","b5at","b5as",false,"📈 Detect Trends");}
}

// ══ TRANSLATE ══
async function genTranslate(){
  $("e5b").style.display="none";
  const description=val("tl_desc");
  const languages=[...document.querySelectorAll(".lang-chip.sel")].map(c=>c.dataset.lang);
  if(!description){$("e5b").textContent="Please paste your description.";$("e5b").style.display="block";return;}
  if(!languages.length){$("e5b").textContent="Select at least one language.";$("e5b").style.display="block";return;}
  ld("b5b","b5bt","b5bs",true,"Translating...");$("r5b").style.display="none";
  try{
    const d=await api("/translate",{description,languages});
    $("tlOut").innerHTML=Object.entries(d).map(([lang,txt])=>`
      <div style="margin-bottom:16px;">
        <div style="font-size:11px;color:var(--muted);font-family:'JetBrains Mono',monospace;text-transform:uppercase;letter-spacing:2px;margin-bottom:8px;">${lang}</div>
        <button class="cpa" style="float:right;" onclick="cpEl('tl_${lang}')">📋 Copy</button>
        <pre id="tl_${lang}">${txt}</pre>
      </div>`).join("");
    show("r5b");
  }catch(e){$("e5b").textContent="Error: "+e.message;$("e5b").style.display="block";}
  finally{ld("b5b","b5bt","b5bs",false,"🌏 Translate Description");}
}
</script>
</body>
</html>"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
