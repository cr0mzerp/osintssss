"""Genişleme tur 2 — hepsi canlı test edildi, authsuz."""
import urllib.parse
from .real import hit, _get

async def search_doaj(client, v, primary):
    out = []
    try:
        r = await _get(client, "https://doaj.org/api/search/articles/" + urllib.parse.quote(primary) + "?pageSize=6")
        if r and r.status_code == 200:
            qt = set(primary.lower().split())
            for a in r.json().get("results", [])[:12]:
                bj = a.get("bibjson", {})
                authors = " ".join(x.get("name", "") for x in bj.get("author", [])[:4])
                if len(qt & set(authors.lower().split())) >= min(2, len(qt)):
                    title = bj.get("title", "")
                    out.append(hit("doaj", (title[:110] if title else authors[:80]),
                                   (bj.get("link") or [{}])[0].get("url", ""), authors[:300]))
                if len(out) >= 5:
                    break
    except Exception:
        pass
    return out

async def search_ietf(client, v, primary):
    out = []
    try:
        r = await _get(client, "https://datatracker.ietf.org/api/v1/person/person/?name__icontains="
                       + urllib.parse.quote(primary) + "&limit=6")
        if r and r.status_code == 200:
            for p in r.json().get("objects", [])[:6]:
                nm = p.get("name", "")
                out.append(hit("ietf", f"{nm} — IETF",
                               f"https://datatracker.ietf.org/person/{nm.replace(' ', '%20')}",
                               (p.get("biography") or "")[:250]))
    except Exception:
        pass
    return out

async def search_sec(client, v, primary):
    out = []
    try:
        from .tr import _get as _g
        r = await _g(client, "https://efts.sec.gov/LATEST/search-index?q=" + urllib.parse.quote(f'"{primary}"')
                     + "&dateRange=custom&startdt=2020-01-01&enddt=2026-10-08")
        if r and r.status_code == 200:
            for h in r.json().get("hits", {}).get("hits", [])[:6]:
                src = h.get("_source", {})
                out.append(hit("sec", f"{src.get('form','?')} — {src.get('ciks','')}",
                               f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={src.get('ciks','')}",
                               f"{src.get('file_date','?')} {src.get('display_names','')}"))
    except Exception:
        pass
    return out

async def search_worldbank(client, v, primary):
    out = []
    try:
        r = await _get(client, "https://search.worldbank.org/api/v3/projects?format=json&qterm="
                       + urllib.parse.quote(primary) + "&rows=5")
        if r and r.status_code == 200:
            projs = (r.json().get("projects") or {})
            items = projs.values() if isinstance(projs, dict) else projs
            for p in list(items)[:5]:
                if isinstance(p, dict):
                    out.append(hit("worldbank", p.get("project_name", primary)[:110],
                                   f"https://projects.worldbank.org/en/projects-operations/project-detail/{p.get('id','')}",
                                   f"{p.get('countryname','?')} {p.get('prodline','?')}"))
    except Exception:
        pass
    return out

async def search_urlscan(client, v, primary):
    out = []
    try:
        nospace = "".join(primary.lower().split())
        r = await _get(client, "https://urlscan.io/api/v1/search/?q=" + urllib.parse.quote(nospace) + "&size=6")
        if r and r.status_code == 200:
            for s in r.json().get("results", [])[:6]:
                page = s.get("page", {})
                out.append(hit("urlscan", page.get("url", "")[:110], s.get("result", ""),
                               f"{page.get('domain','?')} {page.get('country','?')}"))
    except Exception:
        pass
    return out

async def search_nih(client, v, primary):
    out = []
    try:
        parts = primary.split()
        body = {"criteria": {"pi_names": [{"first_name": parts[0], "last_name": parts[-1] if len(parts) > 1 else ""}]}, "limit": 5}
        r = await client.post("https://api.reporter.nih.gov/v2/projects/search", json=body, timeout=10.0,
                              headers={"Content-Type": "application/json", "User-Agent": "OSINT-Platform/1.0"})
        if r.status_code == 200:
            for p in r.json().get("results", [])[:5]:
                out.append(hit("nih", f"{p.get('projectTitle','')[:110]}",
                               f"https://reporter.nih.gov/project-details/{p.get('applId','')}",
                               f"{p.get('contactPiName','?')} {p.get('organization',{}).get('orgName','?')}"))
    except Exception:
        pass
    return out

async def search_usaspending(client, v, primary):
    out = []
    try:
        body = {"filters": {"recipient_search_text": [primary], "award_type_codes": ["A", "B", "C", "D"]},
                "fields": ["Recipient Name", "Award Amount"], "limit": 5, "sort": "Award Amount", "order": "desc"}
        r = await client.post("https://api.usaspending.gov/api/v2/search/spending_by_award/", json=body, timeout=12.0,
                              headers={"Content-Type": "application/json", "User-Agent": "OSINT-Platform/1.0"})
        if r.status_code == 200:
            for a in r.json().get("results", [])[:5]:
                out.append(hit("usaspending", f"{a.get('Recipient Name','')} — ${a.get('Award Amount',0):,.0f}",
                               "https://www.usaspending.gov/search", "ABD federal award kaydı"))
    except Exception:
        pass
    return out

async def search_dailymotion(client, v, primary):
    out = []
    try:
        r = await _get(client, "https://api.dailymotion.com/videos?search=" + urllib.parse.quote(primary)
                       + "&limit=6&fields=id,title,owner.screenname")
        if r and r.status_code == 200:
            for vd in r.json().get("list", [])[:6]:
                out.append(hit("dailymotion", vd.get("title", "")[:110],
                               f"https://www.dailymotion.com/video/{vd.get('id','')}",
                               f"kanal:{vd.get('owner.screenname','?')}"))
    except Exception:
        pass
    return out

async def search_peertube(client, v, primary):
    out = []
    try:
        r = await _get(client, "https://tilvids.com/api/v1/search/videos?search=" + urllib.parse.quote(primary) + "&count=6")
        if r and r.status_code == 200:
            for vd in r.json().get("data", [])[:6]:
                out.append(hit("peertube", vd.get("name", "")[:110], vd.get("url", ""),
                               f"kanal:{(vd.get('channel') or {}).get('displayName','?')}"))
    except Exception:
        pass
    return out

async def search_lemmy(client, v, primary):
    out = []
    try:
        r = await _get(client, "https://lemmy.ml/api/v3/search?q=" + urllib.parse.quote(primary)
                       + "&type_=Users&limit=6", headers={"User-Agent": "OSINT-Platform/1.0"})
        if r and r.status_code == 200:
            for u in r.json().get("users", [])[:6]:
                p = u.get("person", {})
                out.append(hit("lemmy", f"{p.get('display_name') or p.get('name')} — lemmy",
                               p.get("actor_id", ""), (p.get("bio") or "")[:250]))
    except Exception:
        pass
    return out

def _pkg_match(query_nospace: str, text: str) -> bool:
    t = "".join(text.lower().split())
    return query_nospace and query_nospace in t

async def search_packagist(client, v, primary):
    out = []
    try:
        ns = "".join(primary.lower().split())
        r = await _get(client, "https://packagist.org/search.json?q=" + urllib.parse.quote(ns))
        if r and r.status_code == 200:
            for p in r.json().get("results", [])[:15]:
                if _pkg_match(ns, p.get("name", "") + p.get("description", "")):
                    out.append(hit("packagist", f"{p.get('name')} — packagist", p.get("url", ""),
                                   (p.get("description") or "")[:250]))
                if len(out) >= 4:
                    break
    except Exception:
        pass
    return out

async def search_nuget(client, v, primary):
    out = []
    try:
        ns = "".join(primary.lower().split())
        r = await _get(client, "https://azuresearch-usnc.nuget.org/query?q=" + urllib.parse.quote(ns) + "&take=8")
        if r and r.status_code == 200:
            for p in r.json().get("data", [])[:8]:
                if _pkg_match(ns, p.get("id", "") + p.get("description", "")):
                    out.append(hit("nuget", f"{p.get('id')} {p.get('version','')} — NuGet",
                                   f"https://www.nuget.org/packages/{p.get('id','')}",
                                   (p.get("description") or "")[:250]))
    except Exception:
        pass
    return out

async def search_maven(client, v, primary):
    out = []
    try:
        ns = "".join(primary.lower().split())
        r = await _get(client, "https://search.maven.org/solrsearch/select?q=" + urllib.parse.quote(ns)
                       + "&rows=8&wt=json", headers={"User-Agent": "OSINT-Platform/1.0"})
        if r and r.status_code == 200:
            for d in r.json().get("response", {}).get("docs", [])[:8]:
                coord = f"{d.get('g','')}:{d.get('a','')}"
                if _pkg_match(ns, coord):
                    out.append(hit("maven", f"{coord} — Maven Central",
                                   f"https://search.maven.org/artifact/{d.get('g','')}/{d.get('a','')}",
                                   f"v:{d.get('latestVersion','?')}"))
    except Exception:
        pass
    return out

async def search_gbooks(client, v, primary):
    out = []
    try:
        r = await _get(client, "https://www.googleapis.com/books/v1/volumes?q=" + urllib.parse.quote(f'"{primary}"')
                       + "&maxResults=5")
        if r and r.status_code == 200 and r.text.strip().startswith("{"):
            for it in r.json().get("items", [])[:5]:
                vi = it.get("volumeInfo", {})
                out.append(hit("gbooks", f"{vi.get('title','')[:110]} — {', '.join(vi.get('authors', [])[:3])}",
                               vi.get("infoLink", ""), (vi.get("description") or "")[:250]))
    except Exception:
        pass
    return out
