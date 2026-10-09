"""GERÇEK veri dönen connectorlar — hepsi authsuz public API/HTML, parse edilmiş bulgu."""
import json
import re
import urllib.parse
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
API_UA = {"User-Agent": "OSINT-Platform/1.0 (lawful open-data client)", "Accept": "application/json"}
T = 9.0

def hit(source, title, url, snippet="", extra=None, kind="finding"):
    h = {"source": source, "title": title.strip(), "source_url": url,
         "evidence_snippet": snippet.strip()[:500], "kind": kind}
    if extra:
        h.update(extra)
    return h

def guide(source, title, url, snippet=""):
    return hit(source, title, url, snippet, kind="guide")

async def _get(client, url, headers=None, timeout=T):
    try:
        r = await client.get(url, headers=headers or API_UA, timeout=timeout, follow_redirects=True)
        return r
    except Exception:
        return None

# ---- DuckDuckGo web (POST) — LinkedIn/IG/X/TikTok/Telegram/news X-ray ----
async def _ddg_query(client, q: str) -> list:
    import re as _re
    import urllib.parse as _up
    out = []
    try:
        r = await client.post("https://html.duckduckgo.com/html/",
                              data={"q": q}, headers={**UA, "Content-Type": "application/x-www-form-urlencoded"},
                              timeout=12.0)
        if not r or r.status_code != 200:
            return out
        soup = BeautifulSoup(r.text, "lxml")
        for a in soup.select("a.result__a")[:12]:
            title = a.get_text(" ", strip=True)
            href = a.get("href", "")
            m = _re.search(r"uddg=([^&]+)", href)
            url = _up.unquote(m.group(1)) if m else href
            snip = ""
            block = a.find_parent("div", class_="result")
            if block:
                sn = block.select_one(".result__snippet")
                snip = sn.get_text(" ", strip=True) if sn else ""
            if title and url.startswith("http"):
                out.append((title, url, snip))
    except Exception:
        pass
    return out

async def search_ddg(client, v, primary):
    out = []
    for title, url, snip in await _ddg_query(client, f'"{primary}"'):
        out.append(hit("web", title, url, snip))
    return out[:12]

# ---- meslek/sivil iz: federasyon, oda, üniversite, tez, yerel basın ----
async def search_ddg_pro(client, v, primary):
    out = []
    q = f'"{primary}" (avukat OR doktor OR mühendis OR futbolcu OR akademisyen OR tez OR röportaj OR vefat)'
    for title, url, snip in await _ddg_query(client, q):
        out.append(hit("web_pro", title, url, snip))
    return out[:10]

# ---- Wikipedia TR + Wikidata ----
async def search_wiki(client, v, primary):
    out = []
    try:
        r = await _get(client, "https://tr.wikipedia.org/w/api.php?action=query&list=search&srsearch="
                       + urllib.parse.quote(primary) + "&format=json&srlimit=5")
        if r and r.status_code == 200:
            for s in r.json().get("query", {}).get("search", [])[:5]:
                title = s.get("title", "")
                url = "https://tr.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
                snip = re.sub(r"<[^>]+>", "", s.get("snippet", ""))
                extra = {"disambig": True} if "anlam ayrımı" in title.lower() or "şu anlamlara gelebilir" in snip.lower() else None
                out.append(hit("wikipedia", title, url, snip, extra))
    except Exception:
        pass
    try:
        for lang, base in (("tr", "https://tr.wikipedia.org"), ("az", "https://az.wikipedia.org")):
            r = await _get(client, f"{base}/w/api.php?action=query&list=search&srsearch="
                           + urllib.parse.quote(primary) + "&format=json&srlimit=3")
            if r and r.status_code == 200:
                for s in r.json().get("query", {}).get("search", [])[:3]:
                    title = s.get("title", "")
                    if any(h["title"] == title for h in out):
                        continue
                    out.append(hit("wikipedia", f"{title} ({lang}.wiki)",
                                   f"{base}/wiki/" + urllib.parse.quote(title.replace(" ", "_")),
                                   re.sub(r"<[^>]+>", "", s.get("snippet", ""))))
    except Exception:
        pass
    try:
        r = await _get(client, "https://www.wikidata.org/w/api.php?action=wbsearchentities&search="
                       + urllib.parse.quote(primary) + "&language=en&format=json&limit=5")
        if r and r.status_code == 200:
            for e in r.json().get("search", [])[:5]:
                disp = e.get("display", {})
                label = (disp.get("label") or {}).get("value", "")
                desc = (disp.get("description") or {}).get("value", "")
                if label:
                    out.append(hit("wikidata", f"{label} — {desc}",
                                   f"https://www.wikidata.org/wiki/{e.get('id','')}", desc))
    except Exception:
        pass
    return out[:10]

# ---- Bluesky actors (public, authsuz) ----
async def search_bsky(client, v, primary):
    out = []
    try:
        r = await _get(client, "https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors?q="
                       + urllib.parse.quote(primary) + "&limit=8")
        if r and r.status_code == 200:
            for a in r.json().get("actors", [])[:8]:
                handle = a.get("handle", "")
                name = a.get("displayName", "") or handle
                out.append(hit("bluesky", f"{name} (@{handle})",
                               f"https://bsky.app/profile/{handle}",
                               (a.get("description") or "")[:300]))
    except Exception:
        pass
    return out

# ---- Mastodon (public search, authsuz) ----
async def search_mastodon(client, v, primary):
    out = []
    try:
        r = await _get(client, "https://mastodon.social/api/v2/search?q="
                       + urllib.parse.quote(primary) + "&type=accounts&limit=6")
        if r and r.status_code == 200:
            for a in r.json().get("accounts", [])[:6]:
                out.append(hit("mastodon", f"{a.get('display_name') or a.get('username')} (@{a.get('acct')})",
                               a.get("url", ""), re.sub(r"<[^>]+>", "", a.get("note", ""))[:300]))
    except Exception:
        pass
    return out

# ---- GitHub users (public API) ----
async def search_github(client, v, primary):
    import difflib as _d
    out = []
    handles = set(re.sub(r"\W+", "", x.lower()) for x in v["all"])
    try:
        r = await _get(client, "https://api.github.com/search/users?q="
                       + urllib.parse.quote(primary) + "&per_page=10")
        if r and r.status_code == 200:
            for u in r.json().get("items", [])[:10]:
                login = (u.get("login") or "").lower()
                if login in handles or _d.SequenceMatcher(None, login, handles and min(handles, key=len) or "").ratio() >= 0.9:
                    out.append(hit("github", f"@{u.get('login')} — GitHub",
                                   u.get("html_url", ""),
                                   f"id:{u.get('id','?')}"))
    except Exception:
        pass
    return out

# ---- StackExchange users ----
async def search_stack(client, v, primary):
    out = []
    try:
        first = primary.split()[0]
        r = await _get(client, "https://api.stackexchange.com/2.3/users?inname="
                       + urllib.parse.quote(first) + "&site=stackoverflow&pagesize=8")
        if r and r.status_code == 200:
            ql = primary.lower()
            for u in r.json().get("items", [])[:8]:
                dn = u.get("display_name", "")
                if ql.split()[-1][:4] in dn.lower() or dn.lower() in ql:
                    out.append(hit("stackoverflow", f"{dn} — StackOverflow rep:{u.get('reputation')}",
                                   u.get("link", ""), f"rep:{u.get('reputation')} {u.get('location','')}"))
    except Exception:
        pass
    return out[:5]

# ---- Semantic Scholar author ----
async def search_semantic(client, v, primary):
    out = []
    try:
        r = await _get(client, "https://api.semanticscholar.org/graph/v1/author/search?query="
                       + urllib.parse.quote(primary) + "&limit=6&fields=name,affiliations,paperCount,citationCount,url")
        if r and r.status_code == 200:
            for a in r.json().get("data", [])[:6]:
                aff = ", ".join(a.get("affiliations") or [])
                out.append(hit("scholar", f"{a.get('name')} — {a.get('paperCount',0)} makale, {a.get('citationCount',0)} atıf",
                               a.get("url", ""), aff))
    except Exception:
        pass
    return out

# ---- HackerNews (Algolia, public) ----
async def search_hn(client, v, primary):
    out = []
    try:
        r = await _get(client, "https://hn.algolia.com/api/v1/search?query="
                       + urllib.parse.quote(primary) + "&tags=story&hitsPerPage=5")
        if r and r.status_code == 200:
            for h in r.json().get("hits", [])[:5]:
                title = h.get("title", "")
                if title:
                    out.append(hit("hackernews", title,
                                   f"https://news.ycombinator.com/item?id={h.get('objectID','')}",
                                   f"by {h.get('author','?')} points:{h.get('points','?')}"))
    except Exception:
        pass
    return out

# ---- crt.sh — isim geçen sertifikalar ----
async def search_crtsh(client, v, primary):
    out = []
    try:
        nospace = re.sub(r"\W+", "", primary.lower())
        r = await _get(client, f"https://crt.sh/?q=%25{nospace}%25&output=json", timeout=12.0)
        if r and r.status_code == 200:
            try:
                data = r.json()
            except Exception:
                return out
            seen = set()
            for c in data[:20]:
                nv = c.get("name_value", "")
                for line in nv.split("\n"):
                    d = line.strip().lower()
                    if d and d not in seen and nospace in re.sub(r"\W+", "", d):
                        seen.add(d)
                        out.append(hit("certs", d, f"https://crt.sh/?q={urllib.parse.quote(d)}",
                                       f"issuer:{c.get('issuer_name','?')}"))
                        if len(out) >= 6:
                            return out
    except Exception:
        pass
    return out

# ---- GDELT haber (tek sorgu, rate-limit dostu) ----
async def search_gdelt(client, v, primary):
    try:
        r = await _get(client, "https://api.gdeltproject.org/api/v2/doc/doc?query="
                       + urllib.parse.quote(f'"{primary}"') + "&mode=artlist&maxrecords=8&format=json",
                       timeout=12.0)
        if r and r.status_code == 200 and r.text.strip().startswith("{"):
            arts = r.json().get("articles", [])[:8]
            out = []
            for a in arts:
                out.append(hit("news_gdelt", a.get("title", primary), a.get("url", ""),
                               f"{a.get('sourceCommonName','?')} {a.get('seendate','?')}"))
            return out
    except Exception:
        pass
    return []
