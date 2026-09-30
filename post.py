"""
Kannada Gothila daily poster.
1. Asks Claude for a fresh Bangalore joke (avoids repeats via history.json)
2. Renders it as a 1080x1350 card with Pillow
3. Publishes to Instagram via the Graph API

Env vars:
  ANTHROPIC_API_KEY   Claude API key
  IG_USER_ID          Instagram professional account ID
  IG_ACCESS_TOKEN     Long lived access token
  IG_API_HOST         graph.facebook.com (FB login) or graph.instagram.com (IG login)
  IMAGE_BASE_URL      Public base URL where images/ is served (set by the workflow)
  DRY_RUN=1           Generate and render only, skip posting
"""
import json, os, random, re, sys, textwrap, time, datetime, pathlib
import requests
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).parent
HISTORY = ROOT / "history.json"
IMG_DIR = ROOT / "images"
IMG_DIR.mkdir(exist_ok=True)

THEMES = [
    "Silk Board junction traffic", "Outer Ring Road commute", "auto drivers and meter negotiations",
    "rent and deposits (10 months advance)", "Bangalore weather mood swings", "sudden evening rain and flooded roads",
    "startup and tech culture", "filter coffee and darshini breakfast", "Namma Metro", "potholes",
    "house hunting and brokers", "Koramangala vs Indiranagar vs HSR", "weekend plans that die in traffic",
    "Ola/Uber/Rapido surge", "water tankers", "pub culture and last call timings", "BMTC buses",
    "moving to Bangalore for the first time", "learning a few Kannada words", "Nandi Hills sunrise plans",
]

SYSTEM = """You write for 'Kannada Gothila', a light-hearted Instagram meme account about everyday life in Bangalore.
Tone: witty, relatable, affectionate toward the city. Punch at situations (traffic, rent, weather, commutes, startups),
never at any community, language group, migrants, locals, religion, gender, or real named individuals.
Kannada words are welcome when they add flavour (e.g. 'swalpa adjust maadi', 'guru', 'sakkath'), used warmly.
Keep it clean and brand safe."""

PROMPT = """Theme for today: {theme}

Jokes already posted (do not repeat or closely rephrase):
{history}

Return ONLY JSON with keys:
"setup": a short line, max 14 words
"punchline": max 16 words
"caption": 1 to 2 fun sentences for the Instagram caption, no hashtags
"hashtags": list of 6 to 10 hashtags without the # symbol"""


def load_history():
    return json.loads(HISTORY.read_text()) if HISTORY.exists() else []


def generate(history):
    theme = random.choice(THEMES)
    recent = "\n".join(f"- {h['setup']} / {h['punchline']}" for h in history[-60:]) or "(none yet)"
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                 "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5"), "max_tokens": 600,
              "system": SYSTEM,
              "messages": [{"role": "user", "content": PROMPT.format(theme=theme, history=recent)}]},
        timeout=60,
    )
    r.raise_for_status()
    text = r.json()["content"][0]["text"]
    data = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
    data["theme"] = theme
    return data


def font(size, bold=True):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial Bold.ttf", "C:/Windows/Fonts/arialbd.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()


PALETTES = [  # bg, accent, text
    ("#FFD23F", "#E4002B", "#1A1A1A"),  # yellow/red, Kannada flag vibes
    ("#1A1A1A", "#FFD23F", "#FFFFFF"),
    ("#E4002B", "#FFD23F", "#FFFFFF"),
]


def draw_wrapped(d, text, fnt, fill, y, width_chars, W, line_gap=14):
    for line in textwrap.wrap(text, width=width_chars):
        w = d.textlength(line, font=fnt)
        d.text(((W - w) / 2, y), line, font=fnt, fill=fill)
        y += fnt.size + line_gap
    return y


def render(joke, path):
    W, H = 1080, 1350
    bg, accent, fg = random.choice(PALETTES)
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 22], fill=accent)
    d.rectangle([0, H - 22, W, H], fill=accent)

    tag = font(34)
    label = "NAMMA BENGALURU PROBLEMS"
    d.text(((W - d.textlength(label, font=tag)) / 2, 90), label, font=tag, fill=accent)

    y = 330
    y = draw_wrapped(d, joke["setup"], font(64), fg, y, 22, W)
    y += 50
    d.rectangle([W / 2 - 60, y, W / 2 + 60, y + 8], fill=accent)
    y += 70
    draw_wrapped(d, joke["punchline"], font(70), accent, y, 20, W)

    handle = "@kannada.gothila"
    hf = font(36, bold=False)
    d.text(((W - d.textlength(handle, font=hf)) / 2, H - 110), handle, font=hf, fill=fg)
    img.save(path, "JPEG", quality=92)


def publish(image_url, caption):
    host = os.getenv("IG_API_HOST", "graph.facebook.com")
    ver = os.getenv("IG_API_VERSION", "v21.0")
    uid, tok = os.environ["IG_USER_ID"], os.environ["IG_ACCESS_TOKEN"]
    base = f"https://{host}/{ver}/{uid}"
    c = requests.post(f"{base}/media", data={"image_url": image_url, "caption": caption, "access_token": tok}, timeout=60)
    c.raise_for_status()
    cid = c.json()["id"]
    for _ in range(10):  # wait for container to be ready
        s = requests.get(f"https://{host}/{ver}/{cid}", params={"fields": "status_code", "access_token": tok}, timeout=30).json()
        if s.get("status_code") == "FINISHED":
            break
        time.sleep(6)
    p = requests.post(f"{base}/media_publish", data={"creation_id": cid, "access_token": tok}, timeout=60)
    p.raise_for_status()
    return p.json()["id"]


def main():
    history = load_history()
    joke = generate(history)
    stamp = datetime.datetime.utcnow().strftime("%Y%m%d")
    fname = f"{stamp}.jpg"
    render(joke, IMG_DIR / fname)
    caption = f"{joke['caption']}\n\n" + " ".join("#" + h.lstrip("#") for h in joke["hashtags"])
    print(json.dumps(joke, indent=2, ensure_ascii=False))

    if os.getenv("DRY_RUN") == "1":
        print("DRY_RUN: skipped posting"); return
    if os.getenv("STAGE") == "render":  # workflow pushes image first so the URL is live
        (ROOT / "pending.json").write_text(json.dumps({"file": fname, "caption": caption, "joke": joke}, ensure_ascii=False))
        return


def post_pending():
    pend = json.loads((ROOT / "pending.json").read_text())
    url = f"{os.environ['IMAGE_BASE_URL'].rstrip('/')}/images/{pend['file']}"
    media_id = publish(url, pend["caption"])
    history = load_history()
    history.append({**pend["joke"], "date": pend["file"][:8], "media_id": media_id})
    HISTORY.write_text(json.dumps(history, indent=2, ensure_ascii=False))
    (ROOT / "pending.json").unlink()
    print("Posted:", media_id)


if __name__ == "__main__":
    post_pending() if "--publish" in sys.argv else main()
