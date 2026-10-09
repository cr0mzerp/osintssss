"""Global connectorlar — gerçek public API'ler (authsuz)."""
import urllib.parse
from .tr import hit, _get

async def search_interpol(client, v, primary):
    parts = primary.split()
    forename = parts[0] if parts else ""
    name = parts[-1] if len(parts) > 1 else ""
    out = []
    try:
        url = (f"https://ws-public.interpol.int/notices/v1/red?forename={urllib.parse.quote(forename)}"
               f"&name={urllib.parse.quote(name)}&resultPerPage=10&page=1")
        r = await client.get(url, timeout=8.0, headers={"User-Agent": "OSINT-Platform/1.0", "Accept": "application/json"})
        if r.status_code == 200:
            j = r.json()
            for n in (j.get("_embedded", {}).get("notices", [])[:10]):
                title = f"{n.get('forename','')} {n.get('name','')}".strip()
                nid = n.get("entity_id", "")
                out.append(hit("interpol", title or primary,
                               f"https://www.interpol.int/en/How-we-work/Notices/Red-Notices/View-Red-Notices/{nid}",
                               f"DoB:{n.get('date_of_birth','?')} Uyruk:{n.get('nationalities',[])}"))
            if not out:
                out.append(hit("interpol", f"{primary} — Interpol Red tarandı, eşleşme yok",
                               "https://www.interpol.int/en/How-we-work/Notices/Red-Notices/View-Red-Notices",
                               "Public Red Notice'ta eşleşme yok (negatif kanıt)."))
            return out
    except Exception:
        pass
    return [hit("interpol", f"{primary} — Interpol Red",
                "https://www.interpol.int/en/How-we-work/Notices/Red-Notices/View-Red-Notices",
                "forename+name ile public API sorgula.")]

async def search_fbi(client, v, primary):
    out = []
    try:
        url = f"https://api.fbi.gov/wanted/v1/list?title={urllib.parse.quote(primary)}&page=1"
        r = await client.get(url, timeout=8.0, headers={"User-Agent": "OSINT-Platform/1.0"})
        if r.status_code == 200:
            j = r.json()
            for it in (j.get("items", [])[:10]):
                out.append(hit("fbi", it.get("title", primary),
                               it.get("url", "https://www.fbi.gov/wanted"),
                               (it.get("description") or "")[:400]))
            if not out:
                out.append(hit("fbi", f"{primary} — FBI Wanted tarandı, eşleşme yok",
                               "https://www.fbi.gov/wanted",
                               f"Toplam {j.get('total',0)} kayıt içinde title eşleşmesi yok."))
            return out
    except Exception:
        pass
    return [hit("fbi", f"{primary} — FBI Wanted", "https://www.fbi.gov/wanted", "title serbest metinle sorgula.")]

async def search_opensanctions(client, v, primary):
    r = await _get(client, f"https://www.opensanctions.org/search/?q={v['url_ascii']}&scope=sanctions")
    if r and r.status_code == 200:
        txt = r.text.lower()
        # gerçek sonuç sayfasında "No results" yoksa ve isim sonuç kartında geçiyorsa bulgu say
        if "no results" not in txt and "result" in txt and primary.lower() in txt:
            # zayıf sinyal: sayfa arama kutusunu da içerdiği için guide olarak işaretle, skoru merger cap'lesin
            return [hit("opensanctions", f"{primary} — OpenSanctions eşleşme olabilir",
                        f"https://www.opensanctions.org/search/?q={v['url_ascii']}&scope=sanctions",
                        "Sonuç sayfasını açıp kişi kartını doğrula (TR MASAK + AZ FIU dahil).")]
    return [hit("opensanctions", f"{primary} — OpenSanctions",
                f"https://www.opensanctions.org/search/?q={v['url_ascii']}&scope=sanctions",
                "Ücretsiz toplu tarama için targets.simple.csv indirip lokal fuzzy eşleştir.")]

async def search_academic(client, v, primary):
    out = []
    try:
        r = await client.get(f"https://pub.orcid.org/v3.0/search/?q={urllib.parse.quote(primary)}",
                             headers={"Accept": "application/json", "User-Agent": "OSINT-Platform/1.0"}, timeout=8.0)
        if r.status_code == 200:
            n = r.json().get("num-found", 0)
            out.append(hit("orcid", f"{primary} — ORCID {n} kayıt",
                           f"https://orcid.org/orcid-search/search?searchTerm={v['url_ascii']}",
                           f"ORCID public API {n} sonuç döndü."))
    except Exception:
        pass
    try:
        r = await client.get(f"https://api.openalex.org/authors?search={urllib.parse.quote(primary)}",
                             timeout=8.0, headers={"User-Agent": "OSINT-Platform/1.0"})
        if r.status_code == 200:
            res = r.json().get("results", [])[:5]
            for a in res:
                out.append(hit("openalex", a.get("display_name", primary),
                               a.get("id", "https://openalex.org/"),
                               f"Works:{a.get('works_count','?')} Cited:{a.get('cited_by_count','?')}"))
    except Exception:
        pass
    if not out:
        out.append(hit("orcid", f"{primary} — akademik dizin",
                       f"https://orcid.org/orcid-search/search?searchTerm={v['url_ascii']}",
                       "ORCID + OpenAlex + tez.yok.gov.tr manuel tara."))
    return out

async def search_tech(client, v, primary):
    nospace = "".join(primary.lower().split())
    return [
        hit("github", f"{primary} — GitHub kullanıcı",
            f"https://api.github.com/search/users?q={urllib.parse.quote(primary)}",
            "API authsuz 10 req/dk; kullanıcı adı genelde ASCII."),
        hit("crtsh", f"{primary} — Certificate Transparency",
            f"https://crt.sh/?q=%25{nospace}%25&output=json",
            "İsim geçen sertifikaları listeler (domain pivotu)."),
        hit("social_xray", f"{primary} — sosyal X-ray",
            f"https://www.google.com/search?q=%22{urllib.parse.quote(primary)}%22+site:linkedin.com+OR+site:facebook.com+OR+site:instagram.com+OR+site:x.com+OR+site:tiktok.com+OR+site:t.me",
            "Login duvarı için Google X-ray kullan; IG/TikTok kullanıcı adı ASCII varyantla da dene."),
    ]
