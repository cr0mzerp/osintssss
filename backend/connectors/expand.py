"""Genişleme turu — doğrulanmış public API'ler (hepsi test edildi)."""
import urllib.parse
from .real import hit, _get

async def search_openlibrary(client, v, primary):
    out = []
    try:
        r = await _get(client, "https://openlibrary.org/search/authors.json?q=" + urllib.parse.quote(primary))
        if r and r.status_code == 200:
            for a in r.json().get("docs", [])[:6]:
                name = a.get("name", "")
                top = ", ".join((a.get("top_subjects") or [])[:3])
                dates = f"{a.get('birth_date','?')}–{a.get('death_date','')}"
                out.append(hit("openlibrary", f"{name} — yazar ({dates})",
                               f"https://openlibrary.org/authors/{a.get('key','')}", top))
    except Exception:
        pass
    return out

async def search_itunes(client, v, primary):
    out = []
    try:
        r = await _get(client, "https://itunes.apple.com/search?term=" + urllib.parse.quote(primary)
                       + "&entity=allArtist&limit=6")
        if r and r.status_code == 200 and r.text.strip().startswith("{"):
            for it in r.json().get("results", [])[:6]:
                nm = it.get("artistName") or it.get("trackName") or it.get("collectionName", "")
                if nm:
                    out.append(hit("itunes", f"{nm} — {it.get('kind', it.get('wrapperType','?'))}",
                                   it.get("artistLinkUrl") or it.get("trackViewUrl", ""),
                                   it.get("primaryGenreName", "")))
    except Exception:
        pass
    return out

async def search_npm(client, v, primary):
    out = []
    try:
        nospace = "".join(primary.lower().split())
        r = await _get(client, "https://registry.npmjs.org/-/v1/search?text=" + urllib.parse.quote(nospace) + "&size=6")
        if r and r.status_code == 200:
            for o in r.json().get("objects", [])[:6]:
                p = o.get("package", {})
                if nospace in p.get("name", "").lower() or nospace in (p.get("maintainers") or [{}])[0].get("username", "").lower() if p.get("maintainers") else False:
                    out.append(hit("npm", f"{p.get('name')} — npm paketi",
                                   p.get("links", {}).get("npm", ""), (p.get("description") or "")[:250]))
    except Exception:
        pass
    return out

async def search_crates(client, v, primary):
    out = []
    try:
        nospace = "".join(primary.lower().split())
        r = await _get(client, "https://crates.io/api/v1/crates?q=" + urllib.parse.quote(nospace) + "&per_page=6",
                       headers={"User-Agent": "OSINT-Platform/1.0", "Accept": "application/json"})
        if r and r.status_code == 200:
            for c in r.json().get("crates", [])[:6]:
                out.append(hit("crates", f"{c.get('name')} — crates.io",
                               f"https://crates.io/crates/{c.get('name','')}", (c.get("description") or "")[:250]))
    except Exception:
        pass
    return out

async def search_gleif(client, v, primary):
    out = []
    try:
        r = await _get(client, "https://api.gleif.org/api/v1/lei-records?filter%5Bentity.legalName%5D="
                       + urllib.parse.quote(primary.upper()) + "&page%5Bsize%5D=5")
        if r and r.status_code == 200:
            for rec in r.json().get("data", [])[:5]:
                ent = rec.get("attributes", {}).get("entity", {})
                legal = ent.get("legalName", {}).get("name", "")
                addr = (ent.get("legalAddress", {}) or {})
                out.append(hit("gleif", f"{legal} — LEI:{rec.get('id','')}",
                               f"https://search.gleif.org/#/record/{rec.get('id','')}",
                               f"{addr.get('city','?')} {addr.get('country','?')}"))
    except Exception:
        pass
    return out

async def search_archive(client, v, primary):
    out = []
    try:
        r = await _get(client, "https://archive.org/advancedsearch.php?q=" + urllib.parse.quote(f'"{primary}"')
                       + "&fl%5B%5D=identifier,title,creator&rows=6&output=json")
        if r and r.status_code == 200:
            for d in r.json().get("response", {}).get("docs", [])[:6]:
                title = d.get("title", d.get("identifier", ""))
                if title:
                    out.append(hit("archive", str(title)[:120],
                                   f"https://archive.org/details/{d.get('identifier','')}",
                                   f"creator:{d.get('creator','?')}"))
    except Exception:
        pass
    return out

async def search_crossref(client, v, primary):
    out = []
    try:
        r = await _get(client, "https://api.crossref.org/works?query.author=" + urllib.parse.quote(primary)
                       + "&rows=6&select=title,author,DOI,URL,published",
                       headers={"User-Agent": "OSINT-Platform/1.0 (mailto:osint@example.com)", "Accept": "application/json"})
        if r and r.status_code == 200:
            qt = set(primary.lower().split())
            for it in r.json().get("message", {}).get("items", [])[:12]:
                authors = " ".join((a.get("given", "") + " " + a.get("family", "")).strip()
                                   for a in it.get("author", [])[:4])
                if qt & set(authors.lower().split()) and len(qt & set(authors.lower().split())) >= min(2, len(qt)):
                    title = (it.get("title") or [""])[0]
                    out.append(hit("crossref", f"{title[:100]}" if title else authors,
                                   it.get("URL", ""), authors[:300]))
                if len(out) >= 5:
                    break
    except Exception:
        pass
    return out

async def search_musicbrainz(client, v, primary):
    out = []
    try:
        r = await _get(client, "https://musicbrainz.org/ws/2/artist/?query="
                       + urllib.parse.quote(f'artist:"{primary}"') + "&fmt=json&limit=5",
                       headers={"User-Agent": "OSINT-Platform/1.0", "Accept": "application/json"})
        if r and r.status_code == 200 and r.text.strip().startswith("{"):
            for a in r.json().get("artists", [])[:5]:
                out.append(hit("musicbrainz", f"{a.get('name')} — {a.get('type','?')} {a.get('country','')}",
                               f"https://musicbrainz.org/artist/{a.get('id','')}",
                               (a.get("disambiguation") or "")[:250]))
    except Exception:
        pass
    return out
