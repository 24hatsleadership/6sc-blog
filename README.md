# 6 String Creative Blog

Static site for **blog.6stringcreative.com**, hosted on GitHub Pages. Posts are plain Markdown. `build.py` writes `dist/` with no extra packages.

## Add a weekly post

1. Create `content/posts/YYYY-MM-DD-short-slug.md`. The date is the publish date.
2. Start with a header block. `slug` becomes the URL: `https://blog.6stringcreative.com/<slug>/`.
3. Write a standalone article, about 800 to 1200 words, with a short intro, scannable `##` headings, and a `## Do this today` checklist.
4. Put `{{episode}}` on its own line where the podcast box should appear.
5. Commit to `main`. A push rebuilds the site. A post dated in the future waits for its date.

```yaml
---
title: "How Many Google Reviews Do You Need?"
date: 2026-11-03
slug: your-search-phrase
description: "Meta description, about 150 characters, no emoji."
summary: "The short intro shown on the home page and under the title."
author: "6 String Creative"
episode: "4"
minutes: "5"
tag: "Google Business Profile"
video_id: ""
thumbnail: "assets/your-thumb.jpg"
listen: "https://podcast.6stringcreative.com"
---
```

`video_id` is the YouTube id only, the part after `v=` in the watch URL. Leave it empty until the episode is uploaded. An empty id shows the thumbnail instead of an embed. Set `draft: true` to keep a file out of the build entirely.

Checklist items use plain Markdown, not symbols:

```markdown
- [ ] Search your business name on Google Maps.
- A normal bullet is a hyphen too.
```

### Date gate

The build keeps a post only when its date is today or earlier in America/New_York. Future posts stay in the repo and are left out of the HTML, sitemap, and RSS feed.

GitHub Actions also runs on Tuesdays at 16:45 UTC (`45 16 * * 2`), which is 12:45 PM Eastern Daylight Time and 11:45 AM Eastern Standard Time. That is always after 11:30 AM Eastern, so a post dated that Tuesday goes live on the scheduled run even if nobody pushes. You can also run the workflow by hand with `workflow_dispatch`.

Preview a future post locally:

```bash
INCLUDE_FUTURE=1 python3 build.py
```

Preview the site as of a given day:

```bash
AS_OF=2026-10-13 python3 build.py
```

### House rules

- No emojis in posts, titles, descriptions, buttons, or the feed. The build strips any that slip in. Use hyphens and `- [ ]` checklists.
- Do not name vendors, prices, real clients, or a city or region.
- If you cite a number, name the real source and year, and link the source. Do not invent a stat.
- Do not edit `CNAME`.

## Local preview

`python3 build.py`, then open `dist/index.html` or serve `dist/` with any static server.

The hero, avatars, and on-air sign are composited from `art/layers/` with nearest-neighbor scaling:

```bash
pip install pillow
python3 scripts/compose_art.py
```

The committed PNGs are what the site uses. The site build does not need Pillow.

## Hosting

Settings > Pages > Source: **GitHub Actions**. Custom domain: `blog.6stringcreative.com` (also in `CNAME`).
DNS: CNAME record `blog` pointing to `OWNER.github.io`.
