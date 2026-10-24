# -*- coding: utf-8 -*-
"""生成 projects.html —— 全部项目列表页。

数据来源：GitHub API（api.github.com 可用；github.com:443 在本机不通）。
拉下来的原始数据缓存到 _repos.json，API 不可用时用缓存兜底，保证页面总能重建。

用法：
    python build_projects.py            # 重建 projects.html
    python build_projects.py --refresh  # 强制重新拉 API
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "_repos.json"
OUT = HERE / "projects.html"
OWNER = "dcd887"

# 分类：先按名字精确匹配，未命中的进「其他」
GROUPS = [
    ("海关 / 合规业务", [
        "hs-code-assistant", "guandun-agent", "risk-helper",
        "hs-code-api-website", "hs-code-mcp-server",
    ]),
    ("内容作品 · 考据推理", [
        "honglou-tuili", "classics-archive", "classics-emergence",
        "archive-hidden-lodge", "anluo-yiyun", "hertrees-emergent",
    ]),
    ("小工具", ["manga-reader", "fitness-assistant"]),
    ("游戏 / 引擎", ["mcqa", "fleet-ai", "fleet-privacy"]),
    ("MCP 服务与工具链", [
        "minecraft-mcp-server", "mc-modpack-mcp", "mc-rp-assistant-mcp",
        "mc-pack-builder-mcp", "mc-mod-config-mcp", "mc-changelog-mcp",
        "mc-translator-mcp", "game-translator-mcp", "mc-mcp-toolchain",
        "langchain-mcp-agent-demo",
    ]),
    ("站点 / 其他", ["portfolio", "rewriteany-privacy", "dcd887"]),
]
# 未上线 / 开发中，页面上单独标出，不混进「可玩」
WIP = {"hertrees-emergent"}


def token() -> str:
    p = Path(os.environ["USERPROFILE"]) / ".git-credentials"
    m = re.search(r"https://([^:\s]+):([^@\s]+)@github\.com",
                  p.read_text(encoding="utf-8", errors="replace"))
    if not m:
        raise SystemExit("未能从 .git-credentials 解析出 token")
    return m.group(2)


def api(url: str, tok: str):
    req = urllib.request.Request(url, headers={
        "Authorization": "token " + tok,
        "Accept": "application/vnd.github+json",
        "User-Agent": "dsh",
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode() or "{}")


def fetch() -> list[dict]:
    tok = token()
    repos, page = [], 1
    while True:
        batch = api("https://api.github.com/user/repos?per_page=100&page=%d"
                    "&affiliation=owner&sort=pushed" % page, tok)
        if not isinstance(batch, list) or not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    slim = [{
        "name": r["name"],
        "desc": r.get("description") or "",
        "topics": r.get("topics") or [],
        "pages": bool(r.get("has_pages")),
        "homepage": r.get("homepage") or "",
        "pushed": (r.get("pushed_at") or "")[:10],
        "lang": r.get("language") or "",
        "stars": r.get("stargazers_count", 0),
    } for r in repos]
    CACHE.write_text(json.dumps(slim, ensure_ascii=False, indent=1), encoding="utf-8")
    return slim


def load(refresh: bool) -> list[dict]:
    if CACHE.exists() and not refresh:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    try:
        return fetch()
    except Exception as exc:  # noqa: BLE001
        if CACHE.exists():
            print("!! API 拉取失败（%s），改用缓存" % exc)
            return json.loads(CACHE.read_text(encoding="utf-8"))
        raise SystemExit("API 拉取失败且无缓存：%s" % exc)


def live_url(r: dict) -> str:
    if not r["pages"]:
        return ""
    if r["name"].endswith(".github.io"):
        return "https://%s.github.io/" % OWNER
    return "https://%s.github.io/%s/" % (OWNER, r["name"])


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def card(r: dict) -> str:
    url = live_url(r)
    name = esc(r["name"])
    title = '<a href="%s" target="_blank" rel="noopener">%s</a>' % (url, name) if url else name
    badge = ""
    if r["name"] in WIP:
        badge = '<span class="tag wip">开发中 · 未上线</span>'
    elif url:
        badge = '<span class="tag live">线上可访问</span>'
    else:
        badge = '<span class="tag">仓库</span>'
    topics = "".join('<span class="tp">%s</span>' % esc(t) for t in r["topics"][:6])
    meta = " · ".join(x for x in [r["lang"], r["pushed"]] if x)
    return (
        '    <div class="repo">\n'
        '      <div class="rh"><h3>%s</h3>%s</div>\n'
        '      <p>%s</p>\n'
        '      <div class="tps">%s</div>\n'
        '      <div class="meta">%s</div>\n'
        '    </div>\n' % (title, badge, esc(r["desc"]) or "（无描述）", topics, esc(meta))
    )


CSS = """
  :root{--bg:#101214;--card:#181b1f;--border:#262a30;--text:#e8e6e1;--dim:#9a978f;--accent:#a63a2a}
  *{margin:0;padding:0;box-sizing:border-box}
  body{background:var(--bg);color:var(--text);line-height:1.65;padding:0 20px 70px;
       font-family:-apple-system,"PingFang SC","Microsoft YaHei","Noto Sans CJK SC",sans-serif}
  .wrap{max-width:960px;margin:0 auto}
  header{padding:52px 0 28px;border-bottom:1px solid var(--border);margin-bottom:26px}
  h1{font-size:1.7rem;letter-spacing:.02em}
  .sub{color:var(--accent);font-weight:600;margin-top:6px}
  .back{color:var(--dim);font-size:.9rem;text-decoration:none;border-bottom:1px dotted var(--dim)}
  .back:hover{color:var(--text)}
  h2{font-size:1.05rem;margin:34px 0 14px;padding-left:10px;border-left:3px solid var(--accent)}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
  @media(max-width:680px){.grid{grid-template-columns:1fr}header{padding-top:36px}}
  .repo{background:var(--card);border:1px solid var(--border);border-radius:9px;padding:16px 18px}
  .rh{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;margin-bottom:6px}
  .rh h3{font-size:.98rem;font-weight:600;word-break:break-all}
  .rh h3 a{color:var(--text);text-decoration:none}
  .rh h3 a:hover{color:var(--accent)}
  .repo p{color:var(--dim);font-size:.86rem;margin-bottom:9px}
  .tag{font-size:.7rem;padding:2px 7px;border-radius:4px;border:1px solid var(--border);
       color:var(--dim);white-space:nowrap;flex-shrink:0}
  .tag.live{color:#7ec98a;border-color:#2f4a34}
  .tag.wip{color:#d8a44a;border-color:#4a3f2a}
  .tps{margin-bottom:8px}
  .tp{display:inline-block;font-size:.68rem;color:var(--dim);background:#20242a;
      border-radius:3px;padding:1px 6px;margin:0 5px 4px 0}
  .meta{font-size:.72rem;color:#6f6c66}
  footer{margin-top:44px;color:var(--dim);font-size:.8rem;text-align:center}
"""


def main() -> None:
    refresh = "--refresh" in sys.argv
    repos = load(refresh)
    by_name = {r["name"]: r for r in repos}

    used = set()
    blocks = []
    for title, names in GROUPS:
        picked = [by_name[n] for n in names if n in by_name]
        if not picked:
            continue
        used.update(r["name"] for r in picked)
        blocks.append('  <h2>%s<span class="cnt">%d</span></h2>\n  <div class="grid">\n%s  </div>\n'
                      % (title, len(picked), "".join(card(r) for r in picked)))

    rest = [r for r in repos if r["name"] not in used]
    if rest:
        blocks.append('  <h2>其他<span class="cnt">%d</span></h2>\n  <div class="grid">\n%s  </div>\n'
                      % (len(rest), "".join(card(r) for r in rest)))

    live_n = sum(1 for r in repos if live_url(r))
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>全部项目 · 黄谦</title>
<link rel="icon" href="favicon.ico">
<style>%s</style>
</head>
<body>
<div class="wrap">
  <header>
    <a class="back" href="./">← 返回作品集</a>
    <h1>全部项目</h1>
    <div class="sub">%d 个仓库 · %d 个线上可访问站点 · 生成于 %s</div>
  </header>
%s
  <footer>
    本页由 build_projects.py 从 GitHub API 生成，数字与描述均现读仓库，不手工维护。<br>
    标「线上可访问」的均指向 GitHub Pages；标「开发中」的尚未上线。
  </footer>
</div>
</body>
</html>
""" % (CSS, len(repos), live_n, time.strftime("%Y-%m-%d %H:%M"), "".join(blocks))

    OUT.write_text(html, encoding="utf-8", newline="\n")
    print("写出 %s  %d 仓库 / %d 线上" % (OUT.name, len(repos), live_n))
    for title, _ in GROUPS:
        n = sum(1 for r in repos if r["name"] in dict(GROUPS)[title])
        print("  %-18s %d" % (title, n))


if __name__ == "__main__":
    main()
