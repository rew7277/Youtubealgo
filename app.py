import os
import json
import re
from flask import Flask, render_template, request, jsonify
from groq import Groq

app = Flask(__name__)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

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

Return ONLY a valid JSON object — no markdown, no explanation, no backticks. Just raw JSON:
{{
  "titles": ["title1", "title2", "title3", "title4", "title5"],
  "description": "full video description with keywords, call to action, and hashtags",
  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5", "#tag6", "#tag7", "#tag8", "#tag9", "#tag10", "#tag11", "#tag12", "#tag13", "#tag14", "#tag15"],
  "pinned_comment": "engaging pinned comment to boost interaction",
  "ideas": ["idea1", "idea2", "...30 total ideas"],
  "checklist": ["tip1", "tip2", "...12 total tips"]
}}

Rules:
- All 5 titles must be curiosity-driven, SEO-rich, specific to the topic
- Description must include the video URL, keywords, and a subscribe CTA
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
    raw = re.sub(r"^```\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    handle   = data.get("handle", "").strip()
    url      = data.get("url", "").strip()
    topic    = data.get("topic", "").strip()
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
