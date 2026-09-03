"""
AI Content Assistant
---------------------
A Streamlit app that generates ready-to-post social media content
(caption + hashtags) using xAI's Grok model via OpenRouter's FREE tier
(x-ai/grok-4-fast:free).

Why OpenRouter instead of calling xAI directly?
- OpenRouter offers a genuinely free tier for "x-ai/grok-4-fast:free".
- This app is meant to be public. Each visitor enters THEIR OWN free
  OpenRouter API key in the sidebar, so the app owner never pays for
  other people's usage. Keys are kept only in the browser session
  (st.session_state) and are never written to disk or logged.
"""

import json
import time
from datetime import datetime

import requests
import streamlit as st

# --------------------------------------------------------------------------
# Page config & basic styling
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Content Assistant",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
:root {
    --accent: #7C3AED;
}
.stApp {
    background: linear-gradient(180deg, #0f0f1a 0%, #14141f 100%);
}
h1, h2, h3 { font-family: 'Trebuchet MS', sans-serif; }

.hero {
    padding: 1.6rem 1.8rem;
    border-radius: 16px;
    background: linear-gradient(135deg, #7C3AED 0%, #4F46E5 100%);
    color: white;
    margin-bottom: 1.2rem;
}
.hero h1 { margin: 0; font-size: 1.9rem; }
.hero p { margin: 0.35rem 0 0 0; opacity: 0.9; }

.output-card {
    background: #1b1b2b;
    border: 1px solid #2c2c40;
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
}
.hashtag-pill {
    display: inline-block;
    background: #2c2c45;
    color: #c4b5fd;
    padding: 4px 12px;
    border-radius: 999px;
    margin: 3px 4px 3px 0;
    font-size: 0.85rem;
}
.stButton>button {
    background: linear-gradient(135deg, #7C3AED, #4F46E5);
    color: white;
    border: none;
    border-radius: 10px;
    padding: 0.55rem 1.4rem;
    font-weight: 600;
}
.stButton>button:hover { opacity: 0.9; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
FREE_MODEL = "x-ai/grok-4-fast:free"

# --------------------------------------------------------------------------
# Sidebar — API key (BYOK) + generation settings
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🔑 Your API Key")
    st.caption(
        "This app is free & public, so it does **not** ship a shared key. "
        "Paste your own free OpenRouter key below — it stays in your "
        "browser session only, is never saved to a file, and is not "
        "visible to other visitors."
    )
    api_key = st.text_input(
        "OpenRouter API key",
        type="password",
        placeholder="sk-or-v1-...",
        help="Get a free key at https://openrouter.ai/keys",
    )
    st.markdown(
        "[Get a free key →](https://openrouter.ai/keys) · "
        "[Model card](https://openrouter.ai/x-ai/grok-4-fast:free)"
    )

    st.divider()
    st.markdown("## ⚙️ Generation Settings")
    creativity = st.slider("Creativity (temperature)", 0.0, 1.2, 0.8, 0.1)
    variations = st.slider("How many variations?", 1, 3, 1)

    st.divider()
    st.caption("Built with Streamlit · Powered by Grok 4 Fast (free) via OpenRouter")

# --------------------------------------------------------------------------
# Hero header
# --------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero">
        <h1>✨ AI Content Assistant</h1>
        <p>Fill in a few details and get a ready-to-post caption + hashtags in seconds.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Input form
# --------------------------------------------------------------------------
CONTENT_TYPES = [
    "Social Media Post", "Product Launch", "Promotional / Sale",
    "Educational / Tip", "Story / Personal", "Event Announcement",
    "Blog Intro", "Ad Copy", "Video Script Hook",
]
PLATFORMS = [
    "Instagram", "X (Twitter)", "LinkedIn", "Facebook",
    "TikTok", "YouTube (Description)", "Pinterest", "Threads",
]
TONES = [
    "Friendly & casual", "Professional", "Witty / Funny",
    "Inspirational", "Bold & confident", "Minimal / Clean",
    "Luxury / Premium", "Urgent / Sales-driven",
]
LANGUAGES = ["English", "Urdu", "Roman Urdu", "Spanish", "French", "Arabic", "Hindi"]

with st.form("content_form"):
    col1, col2 = st.columns(2)
    with col1:
        content_type = st.selectbox("Content type", CONTENT_TYPES)
        topic = st.text_area(
            "Topic / What is this post about?",
            placeholder="e.g. Launching our new handmade candle collection",
            height=90,
        )
        audience = st.text_input(
            "Target audience",
            placeholder="e.g. Young professionals who like home decor",
        )
    with col2:
        platform = st.selectbox("Platform", PLATFORMS)
        tone = st.selectbox("Tone / Style", TONES)
        language = st.selectbox("Language", LANGUAGES)

    col3, col4, col5 = st.columns(3)
    with col3:
        num_hashtags = st.slider("Number of hashtags", 3, 30, 12)
    with col4:
        include_emojis = st.checkbox("Include emojis", value=True)
    with col5:
        include_cta = st.checkbox("Include call-to-action", value=True)

    extra_notes = st.text_input(
        "Anything else the AI should know? (optional)",
        placeholder="e.g. mention our 20% discount code SAVE20",
    )

    submitted = st.form_submit_button("🚀 Generate Content", use_container_width=True)

# --------------------------------------------------------------------------
# Prompt builder
# --------------------------------------------------------------------------
def build_prompt() -> str:
    parts = [
        f"You are a professional social media copywriter. Write {variations} "
        f"distinct version(s) of a {content_type.lower()} for {platform}.",
        f"Topic: {topic.strip()}",
        f"Target audience: {audience.strip() or 'general audience'}",
        f"Tone/style: {tone}",
        f"Language: {language}",
        f"Emojis: {'use tasteful emojis' if include_emojis else 'do NOT use any emojis'}",
        f"Call to action: {'include one clear call-to-action' if include_cta else 'no explicit call-to-action needed'}",
    ]
    if extra_notes.strip():
        parts.append(f"Extra instructions: {extra_notes.strip()}")

    parts.append(
        f"For EACH version, also generate exactly {num_hashtags} relevant, "
        f"non-generic hashtags (mix of broad and niche) tailored to {platform}."
    )
    parts.append(
        "Respond ONLY with valid JSON, no markdown fences, no commentary, "
        "matching this exact schema:\n"
        '{"versions": [{"caption": "string", "hashtags": ["tag1", "tag2", ...]}]}'
    )
    return "\n".join(parts)


def call_grok(prompt: str, key: str, temperature: float) -> dict:
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        # Recommended by OpenRouter for free-tier usage attribution:
        "HTTP-Referer": "https://streamlit.io",
        "X-Title": "AI Content Assistant",
    }
    payload = {
        "model": FREE_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are an expert social media copywriter. Always reply with strict JSON only.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
    }
    resp = requests.post(OPENROUTER_URL, headers=headers, data=json.dumps(payload), timeout=60)
    resp.raise_for_status()
    data = resp.json()
    raw_text = data["choices"][0]["message"]["content"].strip()

    # Some models occasionally wrap JSON in ```json fences despite instructions.
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        raw_text = raw_text.replace("json\n", "", 1) if raw_text.startswith("json\n") else raw_text

    return json.loads(raw_text)


# --------------------------------------------------------------------------
# Handle submission
# --------------------------------------------------------------------------
if submitted:
    if not api_key.strip():
        st.error("Please paste your free OpenRouter API key in the sidebar first.")
    elif not topic.strip():
        st.error("Please describe the topic of your post.")
    else:
        with st.spinner("Generating your content with Grok..."):
            try:
                prompt = build_prompt()
                result = call_grok(prompt, api_key.strip(), creativity)
                st.session_state["last_result"] = result
                st.session_state["last_meta"] = {
                    "content_type": content_type,
                    "platform": platform,
                    "topic": topic,
                    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                }
            except requests.exceptions.HTTPError as e:
                st.error(f"API error: {e.response.status_code} — {e.response.text[:300]}")
            except (KeyError, json.JSONDecodeError):
                st.error(
                    "The model returned an unexpected format. Please try again "
                    "(you can also lower creativity slightly)."
                )
            except Exception as e:
                st.error(f"Something went wrong: {e}")

# --------------------------------------------------------------------------
# Display results
# --------------------------------------------------------------------------
if "last_result" in st.session_state:
    result = st.session_state["last_result"]
    meta = st.session_state["last_meta"]

    st.markdown("## 📄 Your Generated Content")
    st.caption(f"{meta['content_type']} · {meta['platform']} · generated {meta['generated_at']}")

    download_chunks = []

    for i, version in enumerate(result.get("versions", []), start=1):
        caption = version.get("caption", "")
        hashtags = version.get("hashtags", [])
        hashtag_line = " ".join(f"#{h.lstrip('#')}" for h in hashtags)

        st.markdown(f"### Version {i}")
        st.markdown(
            f"""<div class="output-card">{caption.replace(chr(10), "<br>")}</div>""",
            unsafe_allow_html=True,
        )
        st.markdown(
            "".join(f'<span class="hashtag-pill">#{h.lstrip("#")}</span>' for h in hashtags),
            unsafe_allow_html=True,
        )

        combo = f"{caption}\n\n{hashtag_line}"
        st.text_area(f"Copy-ready text (version {i})", value=combo, height=140, key=f"copyarea_{i}")
        download_chunks.append(f"--- Version {i} ---\n{combo}\n")

        st.divider()

    full_text = "\n".join(download_chunks)
    st.download_button(
        "⬇️ Download all versions (.txt)",
        data=full_text,
        file_name=f"content_{meta['platform'].replace(' ', '_')}_{int(time.time())}.txt",
        mime="text/plain",
        use_container_width=True,
    )
else:
    st.info("Fill the form above and click **Generate Content** to get started.")
