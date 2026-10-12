#!/usr/bin/env python3
"""Static site builder. Reads content/posts/*.md, writes dist/. No dependencies."""
import os, re, html, shutil, glob, json, sys
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "dist")
CFG = json.load(open(os.path.join(ROOT, "site.json")))
SITE = os.environ.get("SITE_BASE", CFG["base"]).rstrip("/")
E = html.escape
AUTHOR = CFG.get("author", "6 String Creative")
MONTHS = "January February March April May June July August September October November December".split()
WEEKDAYS = "Mon Tue Wed Thu Fri Sat Sun".split()
MONS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
RESERVED = {"about", "posts", "assets", "index", "rss", "sitemap", "robots", "404"}
BANNED = ("51 blocks", "51blocks", "pennington", "reviewlead", "trillet")
EMOJI_RE = re.compile(
    "["
    "\U0001F1E0-\U0001F1FF"
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U00002B00-\U00002BFF"
    "\U0000FE0F"
    "\U0000200D"
    "]+"
)
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

def strip_emoji(text, label):
    cleaned, n = EMOJI_RE.subn("", text or "")
    if n:
        print(f"warning: stripped emoji from {label}")
    return cleaned

def reject_banned(text, label):
    low = text.lower()
    for term in BANNED:
        if term in low:
            sys.exit(f"banned term '{term}' in {label}")
    if re.search(r"\$\s?\d", text):
        sys.exit(f"price found in {label}")

def inline(t):
    t = E(t, quote=False)
    def link(m):
        url = m.group(2)
        rel = ' rel="noopener"' if url.startswith("http") else ""
        return f'<a href="{url}"{rel}>{m.group(1)}</a>'
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![*\w])\*([^*]+)\*(?!\w)", r"<em>\1</em>", t)
    return t

def md(text):
    out, para, lst, kind = [], [], [], None
    def flush():
        nonlocal para, lst, kind
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para = []
        if lst:
            tag = "ul" if kind in ("ul", "checks") else "ol"
            cls = ' class="checks"' if kind == "checks" else ""
            out.append(f"<{tag}{cls}>" + "".join(f"<li>{inline(i)}</li>" for i in lst) + f"</{tag}>")
            lst, kind = [], None
    for line in text.splitlines():
        s = line.strip()
        if s == "{{episode}}":
            flush()
            out.append("@@EPISODE@@")
            continue
        m = re.match(r"^(#{2,4})\s+(.*)", s)
        if not s:
            flush()
            continue
        if m:
            flush()
            n = len(m.group(1))
            out.append(f"<h{n}>{inline(m.group(2))}</h{n}>")
            continue
        if s.startswith("> "):
            flush()
            out.append(f"<blockquote><p>{inline(s[2:])}</p></blockquote>")
            continue
        task = re.match(r"^[-*]\s+\[ \]\s+(.*)", s)
        b = re.match(r"^[-*]\s+(.*)", s)
        o = re.match(r"^\d+\.\s+(.*)", s)
        if task or b or o:
            k = "checks" if task else ("ul" if b else "ol")
            if para or (kind and kind != k):
                flush()
            kind = k
            lst.append((task or b or o).group(1))
            continue
        if lst:
            flush()
        para.append(s)
    flush()
    return "\n".join(out)

def today_et():
    override = os.environ.get("AS_OF", "").strip()
    if override:
        return datetime.strptime(override, "%Y-%m-%d").date()
    return datetime.now(ZoneInfo("America/New_York")).date()

def include_future():
    return os.environ.get("INCLUDE_FUTURE", "").strip().lower() in ("1", "true", "yes")

def load_posts(today):
    posts, skipped = [], []
    show_future = include_future()
    for f in sorted(glob.glob(os.path.join(ROOT, "content", "posts", "*.md"))):
        raw = strip_emoji(open(f, encoding="utf-8").read(), os.path.basename(f))
        reject_banned(raw, os.path.basename(f))
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
        meta, body = {}, raw
        if m:
            for line in m.group(1).splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip().strip('"')
            body = m.group(2).strip()
        name = os.path.basename(f)[:-3]
        slug = meta.get("slug") or re.sub(r"^\d{4}-\d{2}-\d{2}-", "", name)
        if not SLUG_RE.match(slug) or slug in RESERVED:
            sys.exit(f"invalid slug '{slug}' in {name}")
        if meta.get("draft", "").lower() == "true":
            continue
        date = meta.get("date", "1970-01-01")
        datetime.strptime(date, "%Y-%m-%d")
        if not show_future and date > today.isoformat():
            skipped.append((slug, date))
            continue
        video = (meta.get("video_id") or "").strip()
        if video.lower() in ("placeholder", "video-id", "todo", "your_youtube_id"):
            video = ""
        summary = strip_emoji(meta.get("summary", ""), slug)
        description = strip_emoji(meta.get("description", "") or summary, slug)
        title = strip_emoji(meta.get("title", slug), slug)
        reject_banned(title + "\n" + description + "\n" + body, slug)
        posts.append(dict(
            slug=slug, title=title, date=date, summary=summary, description=description,
            author=meta.get("author") or AUTHOR, episode=meta.get("episode", ""),
            minutes=meta.get("minutes", ""), tag=meta.get("tag", ""),
            listen=meta.get("listen", "") or CFG.get("podcast_url", ""),
            video_id=video, thumbnail=meta.get("thumbnail", "") or meta.get("image", ""),
            body=md(body),
        ))
    seen = set()
    for p in posts:
        if p["slug"] in seen:
            sys.exit(f"duplicate slug {p['slug']}")
        seen.add(p["slug"])
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts, skipped

def fdate(d):
    dt = datetime.strptime(d, "%Y-%m-%d")
    return f"{MONTHS[dt.month - 1]} {dt.day}, {dt.year}"

def rfc822(d):
    dt = datetime.strptime(d, "%Y-%m-%d")
    return f"{WEEKDAYS[dt.weekday()]}, {dt.day:02d} {MONS[dt.month - 1]} {dt.year} 16:45:00 +0000"

def canon_for(path):
    path = (path or "").strip("/")
    return f"{SITE}/{path}/" if path else f"{SITE}/"

def abs_url(path):
    if not path:
        return ""
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return f"{SITE}/{path.lstrip('/')}"

def jsonld(data):
    blob = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    return f'<script type="application/ld+json">{blob}</script>'

def layout(title, desc, path, body, prefix="", og_type="website", image=None, extra=""):
    nav = "".join(
        f'<a href="{href if href.startswith("http") else prefix + href}">{E(label)}</a>'
        for label, href in CFG["nav"]
    )
    soc = "".join(f'<a href="{u}" rel="noopener">{E(l)}</a>' for l, u in CFG["social"])
    canon = canon_for(path)
    full_title = title if title == CFG["name"] else f"{title} | {CFG['name']}"
    img = ""
    if image:
        src = abs_url(image)
        img = (
            f'<meta property="og:image" content="{E(src)}">'
            f'<meta property="og:image:alt" content="{E(title)}">'
            f'<meta name="twitter:image" content="{E(src)}">'
        )
    card = "summary_large_image" if image else "summary"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(full_title)}</title><meta name="description" content="{E(desc)}">
<link rel="canonical" href="{canon}"><meta name="theme-color" content="{CFG['theme_color']}">
<meta property="og:title" content="{E(full_title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:type" content="{og_type}"><meta property="og:url" content="{canon}"><meta property="og:site_name" content="{E(CFG['name'])}">
{img}<meta name="twitter:card" content="{card}"><meta name="twitter:title" content="{E(full_title)}"><meta name="twitter:description" content="{E(desc)}">
<link rel="alternate" type="application/rss+xml" title="{E(CFG['name'])}" href="{SITE}/rss.xml">
<link rel="icon" href="{prefix}assets/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{CFG['font_url']}">
<link rel="stylesheet" href="{prefix}assets/style.css">
{extra}
</head><body><a class="skip" href="#main">Skip to content</a>
<header class="site"><div class="wrap"><a class="brand" href="{prefix}index.html" aria-label="{E(CFG['name'])} home"><img src="{CFG['logo']}" alt="{E(CFG['brand'])}"></a>
<nav aria-label="Main">{nav}</nav><a class="btn btn-sm hdr-cta" href="{CFG['cta_url']}">{E(CFG['cta_label'])}</a></div></header>
<main id="main">{body}</main>
<footer class="site"><div class="wrap"><div class="cols"><p>{CFG['footer_blurb']}</p><a href="{CFG['main_url']}" aria-label="{E(CFG['brand'])}"><img src="{CFG['logo']}" alt="{E(CFG['brand'])}"></a></div>
<div class="soc">{soc}</div><p class="fine">{CFG['copyright']}</p></div></footer></body></html>"""

def avatars(prefix):
    return (
        f'<img class="avatar pixel-art" src="{prefix}{CFG["avatar_dan"]}" alt="Dan" width="944" height="752">'
        f'<img class="avatar pixel-art" src="{prefix}{CFG["avatar_kate"]}" alt="Kate" width="720" height="712">'
    )

def card(p, prefix=""):
    chip = f'<span class="chip">Ep {E(p["episode"])}</span>' if p["episode"] else ""
    eyebrow = f'{chip}{E(p["tag"])}' if p["tag"] else chip or E(fdate(p["date"]))
    show = ""
    if p["episode"]:
        show = f'<p class="from-show">{avatars(prefix)}<span class="pixel">From the podcast</span></p>'
    href = f'{prefix}{p["slug"]}/'
    return (
        f'<article class="card"><p class="eyebrow">{eyebrow}</p>'
        f'<h3><a href="{href}">{E(p["title"])}</a></h3><p>{E(p["summary"])}</p>'
        f'{show}<p class="byline">By {E(p["author"])} · {E(fdate(p["date"]))}</p>'
        f'<a class="more" href="{href}">{E(CFG["read_label"])}</a></article>'
    )

def episode_html(p, prefix):
    label = f"Episode {p['episode']}" if p["episode"] else "Marketing Tune-Up"
    title = f"Marketing Tune-Up, {label}" if p["episode"] else "Marketing Tune-Up"
    if p["video_id"]:
        media = (
            f'<div class="embed"><iframe src="https://www.youtube-nocookie.com/embed/{E(p["video_id"])}" '
            f'title="{E(title)}" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe></div>'
        )
    elif p["thumbnail"]:
        media = (
            f'<figure class="thumb"><img class="pixel-art" src="{prefix}{p["thumbnail"]}" alt="{E(title)}" width="1920" height="1080" loading="lazy" decoding="async"></figure>'
        )
    else:
        media = ""
    listen = p["listen"] or "https://podcast.6stringcreative.com"
    return (
        f'<section class="episode-box" aria-label="Podcast episode">'
        f'<h2 class="pixel bar">From the podcast</h2><div class="episode-body">'
        f'<div class="hosts">{avatars(prefix)}<p><strong>{E(title)}</strong><br>Dan and Kate host this episode.</p></div>'
        f'{media}<p class="actions"><a class="btn" href="{E(listen)}">Listen to the full episode</a></p>'
        f'</div></section>'
    )

def article_json(p, canon):
    data = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": p["title"],
        "description": p["description"],
        "datePublished": p["date"],
        "dateModified": p["date"],
        "author": {"@type": "Organization", "name": p["author"], "url": "https://6stringcreative.com"},
        "publisher": {
            "@type": "Organization",
            "name": CFG["brand"],
            "url": "https://6stringcreative.com",
            "logo": {"@type": "ImageObject", "url": CFG["logo"]},
        },
        "mainEntityOfPage": {"@type": "WebPage", "@id": canon},
        "url": canon,
        "inLanguage": "en-US",
    }
    if p["thumbnail"]:
        data["image"] = [abs_url(p["thumbnail"])]
    if p["tag"]:
        data["articleSection"] = p["tag"]
    return jsonld(data)

def blog_json():
    return jsonld({
        "@context": "https://schema.org",
        "@type": "Blog",
        "name": CFG["name"],
        "url": f"{SITE}/",
        "description": CFG["desc"],
        "publisher": {"@type": "Organization", "name": CFG["brand"], "url": "https://6stringcreative.com"},
        "inLanguage": "en-US",
    })

def write(path, content):
    full = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "w", encoding="utf-8").write(content)

def stage(prefix=""):
    src = CFG.get("hero_image")
    if not src:
        return ""
    w, h = CFG.get("hero_width", 1920), CFG.get("hero_height", 900)
    return (
        f'<figure class="stage"><img class="pixel-art stage-bg" src="{prefix}{src}" alt="{E(CFG.get("hero_image_alt", ""))}" '
        f'width="{w}" height="{h}" fetchpriority="high" decoding="async">'
        f'<img class="pixel-art onair off" src="{prefix}{CFG["onair_off"]}" alt="" aria-hidden="true" width="280" height="120"></figure>'
    )

def assert_output_clean():
    for dirpath, _, files in os.walk(OUT):
        for name in files:
            if not name.endswith((".html", ".xml", ".txt", ".css")):
                continue
            path = os.path.join(dirpath, name)
            raw = open(path, encoding="utf-8").read()
            if EMOJI_RE.search(raw):
                sys.exit(f"emoji found in output {os.path.relpath(path, OUT)}")
            low = raw.lower()
            for term in BANNED:
                if term in low:
                    sys.exit(f"banned term '{term}' in output {os.path.relpath(path, OUT)}")

def main():
    today = today_et()
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    shutil.copytree(os.path.join(ROOT, "assets"), os.path.join(OUT, "assets"))
    posts, skipped = load_posts(today)
    sec = CFG["section"]
    hero_image = CFG.get("hero_image", "")
    cards = "\n".join(card(p) for p in posts) or "<p>New posts are on the way.</p>"
    hero = (
        f'<section class="hero"><div class="wrap hero-grid">{stage()}'
        f'<div class="hero-copy"><p class="eyebrow">{E(CFG["hero_eyebrow"])}</p><h1>{E(CFG["hero_title"])}</h1>'
        f'<p class="lede">{E(CFG["hero_lede"])}</p><p class="actions">'
        f'<a class="btn" href="{sec}/">{E(CFG["hero_btn1"])}</a>'
        f'<a class="btn btn-ghost" href="{CFG["hero_btn2_url"]}">{E(CFG["hero_btn2"])}</a></p></div></div></section>'
    )
    latest = (
        f'<section class="band"><div class="wrap"><p class="eyebrow">{E(CFG["latest_eyebrow"])}</p>'
        f'<h2>{E(CFG["latest_title"])}</h2><div class="grid">{"".join(card(p) for p in posts[:12]) or "<p>New posts are on the way.</p>"}</div>'
        f'<p class="allp"><a class="more" href="{sec}/">{E(CFG["all_label"])}</a></p></div></section>'
    )
    cta = (
        f'<section class="cta"><div class="wrap"><h2>{E(CFG["cta_title"])}</h2><p>{E(CFG["cta_text"])}</p>'
        f'<p><a class="btn" href="{CFG["cta_url"]}">{E(CFG["cta_label"])}</a></p></div></section>'
    )
    write("index.html", layout(CFG["name"], CFG["desc"], "", hero + latest + cta, image=hero_image, extra=blog_json()))
    archive_cards = "\n".join(card(p, "../") for p in posts) or "<p>New posts are on the way.</p>"
    write(
        f"{sec}/index.html",
        layout(CFG["section_title"], CFG["desc"], sec,
               f'<section class="page"><div class="wrap"><p class="eyebrow">{E(CFG["name"])}</p><h1>{E(CFG["section_title"])}</h1><div class="grid">{archive_cards}</div></div></section>',
               prefix="../", image=hero_image),
    )
    about = "".join(f"<p>{E(t)}</p>" for t in CFG["about"])
    write("about/index.html", layout("About", CFG["desc"], "about",
        f'<section class="page"><div class="wrap narrow"><p class="eyebrow">{E(CFG["name"])}</p><h1>About</h1><div class="prose">{about}</div></div></section>' + cta,
        prefix="../", image=hero_image))
    for p in posts:
        canon = canon_for(p["slug"])
        meta_bits = [
            f"Episode {p['episode']}" if p["episode"] else "",
            fdate(p["date"]),
            f"{p['minutes']} min listen" if p["minutes"] and p["episode"] else (f"{p['minutes']} min" if p["minutes"] else ""),
            p["tag"],
        ]
        meta = " · ".join(x for x in meta_bits if x)
        block = episode_html(p, "../")
        prose = p["body"].replace("@@EPISODE@@", block) if "@@EPISODE@@" in p["body"] else p["body"] + block
        extra = (
            f'<meta property="article:published_time" content="{p["date"]}">'
            f'<meta property="article:author" content="{E(p["author"])}">'
            + article_json(p, canon)
        )
        body = (
            f'<article class="page"><div class="wrap narrow"><p class="eyebrow">{E(meta)}</p>'
            f'<h1>{E(p["title"])}</h1><p class="byline">By {E(p["author"])}</p>'
            f'<p class="lede">{E(p["summary"])}</p><div class="prose">{prose}</div>'
            f'<p class="back"><a class="more" href="../{sec}/">{E(CFG["back_label"])}</a></p></div></article>' + cta
        )
        write(f"{p['slug']}/index.html", layout(p["title"], p["description"], p["slug"], body, prefix="../", og_type="article", image=p["thumbnail"] or hero_image, extra=extra))
    write("404.html", layout("Page not found", CFG["desc"], "404",
        '<section class="page"><div class="wrap narrow"><h1>Page not found</h1><p class="lede">That page moved or never existed.</p><p><a class="btn" href="/">Back home</a></p></div></section>',
        image=hero_image))
    items = "".join(
        f'<item><title>{E(p["title"])}</title><link>{SITE}/{p["slug"]}/</link>'
        f'<guid isPermaLink="true">{SITE}/{p["slug"]}/</guid><pubDate>{rfc822(p["date"])}</pubDate>'
        f'<description>{E(p["description"])}</description><dc:creator>{E(p["author"])}</dc:creator></item>'
        for p in posts
    )
    write("rss.xml",
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel>'
        f'<title>{E(CFG["name"])}</title><link>{SITE}/</link><description>{E(CFG["desc"])}</description>'
        f'<language>en-us</language><lastBuildDate>{rfc822(today.isoformat())}</lastBuildDate>{items}</channel></rss>')
    urls = [("", today.isoformat()), (f"{sec}/", today.isoformat()), ("about/", today.isoformat())]
    urls += [(f"{p['slug']}/", p["date"]) for p in posts]
    write("sitemap.xml",
        '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(f"<url><loc>{SITE}/{u}</loc><lastmod>{d}</lastmod></url>" for u, d in urls)
        + "</urlset>")
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")
    shutil.copy(os.path.join(ROOT, "CNAME"), os.path.join(OUT, "CNAME"))
    open(os.path.join(OUT, ".nojekyll"), "w").close()
    assert_output_clean()
    gate = "future posts included" if include_future() else "future posts skipped"
    print(f"Built {len(posts)} post(s) as of {today.isoformat()} America/New_York ({gate}).")
    for slug, date in skipped:
        print(f"  skipped {slug} ({date})")

if __name__ == "__main__":
    main()
