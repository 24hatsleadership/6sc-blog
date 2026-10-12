# 6 String Creative Blog

Static site for **blog.6stringcreative.com**, hosted on GitHub Pages.

## Add content
1. Add a Markdown file to `content/posts/` named `YYYY-MM-DD-short-slug.md`.
2. Start it with a header block (`title`, `date`, `summary`, optional `tag`).
3. Commit to `main`. GitHub Actions rebuilds and deploys automatically.

Set `draft: true` in the header block to keep a post unpublished.

## Local preview
`python3 build.py` then open `dist/index.html`.

## Hosting
Settings > Pages > Source: **GitHub Actions**. Custom domain: `blog.6stringcreative.com` (also in `CNAME`).
DNS: CNAME record `blog` pointing to `OWNER.github.io`.
