"""
AI Content Assistant
---------------------
A Streamlit app that generates ready-to-post social media content
(caption + hashtags) using Groq's ultra-fast free-tier LLM API
(GroqCloud — https://console.groq.com).

Why each visitor uses their own Groq key:
- This app is meant to be public. Groq's free tier has per-key rate
  limits, so if everyone shared one key it would run out fast and you'd
  be on the hook for it. Instead, each visitor pastes THEIR OWN free
  Groq API key in the sidebar. Keys are kept only in that browser's
  session (st.session_state) and are never written to disk or logged.
"""

import json
import time
from datetime import datetime

import requests
import streamlit as st

# --------------------------------------------------------------------------
# Page config & design system
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Content Assistant",
    page_icon="🗞️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Design concept: a "content desk" — the visual language of an editorial
# proofing room, not a generic SaaS dashboard. Deep ink-navy surfaces,
# a warm brass/gold accent standing in for an editor's pen, a serif
# display face for headings paired with a plain-spoken sans for UI and
# body text. Flat surfaces with hairline rules instead of shadows or
# gradients; the caption itself — not chrome — is the focal point.
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,500;0,9..144,600;1,9..144,500&family=Inter:wght@400;500;600&display=swap');

:root {
    --bg: #12161C;
    --surface: #171D25;
    --surface-2: #1D2530;
    --border: #2B3542;
    --text: #EAE6DC;
    --text-muted: #8C96A6;
    --accent: #D2A441;
    --accent-strong: #E8BE68;
    --accent-ink: #1A1305;
}

.stApp { background: var(--bg); color: var(--text); }
[data-testid="stAppViewContainer"], [data-testid="stHeader"] { background: var(--bg); }
html, body, [class*="css"] { font-family: 'Inter', -apple-system, sans-serif; }
h1, h2, h3, h4 { font-family: 'Fraunces', Georgia, serif; font-weight: 500; color: var(--text); }

/* ---- Masthead ---- */
.masthead { padding: 0.4rem 0 1.6rem 0; margin-bottom: 1.6rem; border-bottom: 1px solid var(--border); }
.masthead h1 {
    font-size: 2.4rem; font-style: italic; margin: 0; letter-spacing: -0.01em; line-height: 1.15;
}
.masthead p {
    font-family: 'Inter', sans-serif; color: var(--text-muted); margin: 0.5rem 0 0 0;
    font-size: 1rem; max-width: 46ch;
}

/* ---- Sidebar ---- */
section[data-testid="stSidebar"] {
    background: var(--surface); border-right: 1px solid var(--border);
}
section[data-testid="stSidebar"] h3 {
    font-family: 'Fraunces', serif; font-style: italic; font-weight: 500;
    font-size: 1.15rem; color: var(--text); margin-bottom: 0.2rem;
}
section[data-testid="stSidebar"] .stCaption, section[data-testid="stSidebar"] small {
    color: var(--text-muted);
}
section[data-testid="stSidebar"] a { color: var(--accent-strong); text-decoration: none; border-bottom: 1px solid rgba(210,164,65,0.4); }
section[data-testid="stSidebar"] a:hover { border-bottom-color: var(--accent-strong); }

/* ---- Inputs ---- */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    background: var(--surface-2) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 6px !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: none !important;
}
label, .stSlider label, .stCheckbox label p { color: var(--text) !important; font-size: 0.92rem; }

/* Slider */
div[data-baseweb="slider"] div[role="slider"] { background: var(--accent) !important; border-color: var(--accent) !important; }
div[data-baseweb="slider"] > div > div:nth-child(2) { background: var(--accent) !important; }

/* Checkbox */
[data-testid="stCheckbox"] svg { color: var(--accent) !important; }

/* ---- Buttons ---- */
.stButton > button, [data-testid="stFormSubmitButton"] button, [data-testid="stDownloadButton"] button {
    background: var(--accent);
    color: var(--accent-ink);
    border: none;
    border-radius: 5px;
    padding: 0.6rem 1.4rem;
    font-weight: 600;
    font-family: 'Inter', sans-serif;
    transition: background 0.15s ease;
}
.stButton > button:hover, [data-testid="stFormSubmitButton"] button:hover, [data-testid="stDownloadButton"] button:hover {
    background: var(--accent-strong);
    color: var(--accent-ink);
}
[data-testid="stDownloadButton"] button {
    background: transparent; color: var(--accent-strong); border: 1px solid var(--border);
}
[data-testid="stDownloadButton"] button:hover { border-color: var(--accent); color: var(--accent-strong); background: var(--surface-2); }

/* ---- Form card ---- */
[data-testid="stForm"] {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1.6rem 1.8rem 1.2rem 1.8rem;
}

/* ---- Section labels ---- */
.section-label {
    font-family: 'Fraunces', serif; font-style: italic; font-weight: 500;
    color: var(--accent-strong); font-size: 1.05rem; margin: 0 0 0.15rem 0;
    padding-left: 0.7rem; border-left: 2px solid var(--accent);
}
.section-meta { color: var(--text-muted); font-size: 0.85rem; margin: 0.1rem 0 1.1rem 0.75rem; }

/* ---- Output ---- */
.version-label {
    font-family: 'Fraunces', serif; font-style: italic; font-size: 1rem;
    color: var(--text-muted); margin: 1.1rem 0 0.5rem 0;
}
.output-card {
    background: var(--surface);
    border-left: 3px solid var(--accent);
    border-radius: 4px;
    padding: 1.1rem 1.3rem;
    margin-bottom: 0.7rem;
    font-size: 1.02rem;
    line-height: 1.65;
    color: var(--text);
}
.hashtag-pill {
    display: inline-block;
    background: transparent;
    border: 1px solid var(--border);
    color: var(--accent-strong);
    padding: 3px 11px;
    border-radius: 4px;
    margin: 3px 5px 3px 0;
    font-size: 0.82rem;
}
hr { border-color: var(--border) !important; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# A few solid, free-tier-friendly models on GroqCloud. The first one is
# used by default; visitors can switch in the sidebar.
# Groq deprecated llama-3.3-70b-versatile, llama-3.1-8b-instant, and
# gemma2-9b-it. These are their current recommended replacements
# (verified against console.groq.com/docs/deprecations).
GROQ_MODELS = {
    "GPT-OSS 120B (best quality)": "openai/gpt-oss-120b",
    "GPT-OSS 20B (fastest)": "openai/gpt-oss-20b",
    "Qwen 3.6 27B": "qwen/qwen3.6-27b",
    "Llama 4 Maverick 17B": "meta-llama/llama-4-maverick-17b-128e-instruct",
}

# --------------------------------------------------------------------------
# Sidebar — API key (BYOK) + generation settings
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Your API key")
    st.caption(
        "This app is free and public, so it doesn't ship a shared key. "
        "Paste your own free Groq key below — it stays in your browser "
        "session only and is never saved or shown to other visitors."
    )
    api_key = st.text_input(
        "Groq API key",
        type="password",
        placeholder="gsk_...",
        help="Get a free key at https://console.groq.com/keys",
        label_visibility="collapsed",
    )
    st.markdown(
        "[Get a free key](https://console.groq.com/keys) · "
        "[Model list](https://console.groq.com/docs/models)"
    )

    st.divider()
    st.markdown("### Settings")
    model_label = st.selectbox("Model", list(GROQ_MODELS.keys()))
    selected_model = GROQ_MODELS[model_label]
    creativity = st.slider("Creativity", 0.0, 1.2, 0.8, 0.1)
    variations = st.slider("Variations", 1, 3, 1)

    st.divider()
    st.caption("Built with Streamlit. Powered by Groq's free tier.")

# --------------------------------------------------------------------------
# Masthead
# --------------------------------------------------------------------------
st.markdown(
    """
    <div class="masthead">
        <h1>AI Content Assistant</h1>
        <p>Set the brief — type, topic, audience, platform — and get a caption with hashtags, ready to post.</p>
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

    submitted = st.form_submit_button("Generate content", use_container_width=True)

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


def call_groq(prompt: str, key: str, temperature: float, model: str) -> dict:
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are an expert social media copywriter. Always reply with strict JSON only.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }
    resp = requests.post(GROQ_URL, headers=headers, data=json.dumps(payload), timeout=60)
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
        st.error("Please paste your free Groq API key in the sidebar first.")
    elif not topic.strip():
        st.error("Please describe the topic of your post.")
    else:
        with st.spinner(f"Generating your content with {model_label}..."):
            try:
                prompt = build_prompt()
                result = call_groq(prompt, api_key.strip(), creativity, selected_model)
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

    st.markdown('<p class="section-label">Your content</p>', unsafe_allow_html=True)
    st.markdown(
        f'<p class="section-meta">{meta["content_type"]} · {meta["platform"]} · generated {meta["generated_at"]}</p>',
        unsafe_allow_html=True,
    )

    download_chunks = []

    for i, version in enumerate(result.get("versions", []), start=1):
        caption = version.get("caption", "")
        hashtags = version.get("hashtags", [])
        hashtag_line = " ".join(f"#{h.lstrip('#')}" for h in hashtags)

        if len(result.get("versions", [])) > 1:
            st.markdown(f'<p class="version-label">Version {i}</p>', unsafe_allow_html=True)
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
        "Download all versions (.txt)",
        data=full_text,
        file_name=f"content_{meta['platform'].replace(' ', '_')}_{int(time.time())}.txt",
        mime="text/plain",
        use_container_width=True,
    )
else:
    st.info("Fill in the brief above and click **Generate content** to get started.")
