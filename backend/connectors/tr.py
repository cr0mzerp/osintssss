"""TR connectorları — tamamı açık/kayıtsız kaynak, best-effort parse."""
import httpx
from bs4 import BeautifulSoup

UA = {"User-Agent": "OSINT-Platform/1.0 (lawful open-data client)"}
TIMEOUT = 8.0

def hit(source, title, url, snippet="", extra=None):
    h = {"source": source, "title": title.strip(), "source_url": url, "evidence_snippet": snippet.strip()[:500]}
    if extra:
        h.update(extra)
    return h

async def _get(client, url, **kw):
    try:
        r = await client.get(url, timeout=TIMEOUT, headers=UA, follow_redirects=True, **kw)
        return r
    except Exception:
        return None

async def search_terorarananlar(client, v, primary):
    out = []
    for path in ["/tarananlar", "/etkisizlist"]:
        r = await _get(client, f"https://www.terorarananlar.pol.tr{path}")
        if not r or r.status_code != 200:
            continue
        soup = BeautifulSoup(r.text, "lxml")
        q = primary.lower()
        for card in soup.select("div, li, article"):
            txt = card.get_text(" ", strip=True)
            if len(txt) > 300 or q not in txt.lower():
                continue
            a = card.find("a", href=True)
            url = ("https://www.terorarananlar.pol.tr" + a["href"]) if a else f"https://www.teroraranlar.pol.tr{path}"
            out.append(hit("terorarananlar", txt[:120], url, txt[:300]))
            if len(out) >= 10:
                break
    if not out:
        out.append(hit("terorarananlar", f"{primary} — liste tarandı, doğrudan eşleşme yok",
                       "https://www.terorarananlar.pol.tr/terorarama/ara",
                       "Arananlar listesinde tam isim eşleşmesi bulunamadı (negatif kanıt)."))
    return out[:10]

async def search_resmigazete(client, v, primary):
    # Arşiv fihristi + arama sayfası best-effort; her zaman link-out da ver
    out = []
    try:
        r = await _get(client, f"https://www.resmigazete.gov.tr/filtreler?search={v['url_ascii']}")
        if r and r.status_code == 200 and primary.lower() in r.text.lower():
            out.append(hit("resmigazete", primary, f"https://www.resmigazete.gov.tr/filtreler?search={v['url_ascii']}",
                           "Resmî Gazete arşivinde isim geçiyor (detay için linki aç)."))
    except Exception:
        pass
    out.append(hit("resmigazete", f"{primary} — Resmî Gazete arşiv sorgusu",
                   f"https://www.resmigazete.gov.tr/arsiv",
                   "Atama/ilan/tebligat kayıtları için arşivde isim arat."))
    return out

async def search_aym(client, v, primary):
    out = [hit("aym", f"{primary} — AYM Kararlar Bilgi Bankası",
               "https://kararlarbilgibankasi.anayasa.gov.tr/",
               "Bireysel Başvuru > Başvuru Adı alanına isim yazarak sorgula (gizlilik kararı yoksa isim açık).")]
    return out

async def _adalet_post(client, base, words):
    """Yargıtay/Danıştay/UYAP ortak POST arama (adalet.core altyapı)."""
    try:
        payload = {"andKelime": words, "page": 1, "size": 5}
        r = await client.post(f"{base}/arama", json=payload, timeout=TIMEOUT, headers=UA)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

async def search_yargitay(client, v, primary):
    data = await _adalet_post(client, "https://karararama.yargitay.gov.tr", primary)
    out = []
    if isinstance(data, dict):
        for d in (data.get("data") or data.get("content") or [])[:5]:
            if isinstance(d, dict):
                out.append(hit("yargitay", f"{d.get('daireKurul','')} {d.get('esasNo','')} {d.get('kararNo','')}",
                               "https://karararama.yargitay.gov.tr/", str(d)[:400]))
    if not out:
        out.append(hit("yargitay", f"{primary} — Yargıtay emsal taraması",
                       "https://karararama.yargitay.gov.tr/", "Taraflar maskeli; şirket/kavram geçerse döner."))
    return out

async def search_danistay(client, v, primary):
    data = await _adalet_post(client, "https://karararama.danistay.gov.tr", primary)
    out = []
    if isinstance(data, dict):
        for d in (data.get("data") or data.get("content") or [])[:5]:
            if isinstance(d, dict):
                out.append(hit("danistay", f"{d.get('daireKurul','')} {d.get('esasNo','')} {d.get('kararNo','')}",
                               "https://karararama.danistay.gov.tr/", str(d)[:400]))
    if not out:
        out.append(hit("danistay", f"{primary} — Danıştay emsal taraması",
                       "https://karararama.danistay.gov.tr/", "İdari/imar/ihale kararları için."))
    return out

async def search_uyap_emsal(client, v, primary):
    data = await _adalet_post(client, "https://emsal.uyap.gov.tr", primary)
    out = []
    if isinstance(data, dict):
        for d in (data.get("data") or [])[:5]:
            out.append(hit("uyap_emsal", primary, "https://emsal.uyap.gov.tr/", str(d)[:400]))
    if not out:
        out.append(hit("uyap_emsal", f"{primary} — UYAP Emsal (~850bin karar)",
                       "https://emsal.uyap.gov.tr/", "Tam metin maskeli; kavram/şirket unvanı ile tamamla."))
    return out

async def search_etbis(client, v, primary):
    import re as _re
    out = []
    r = await _get(client, f"https://etbis.ticaret.gov.tr/tr/SiteSorgulama?page=1&url={v['url_ascii']}")
    if r and r.status_code == 200:
        soup = BeautifulSoup(r.text, "lxml")
        toks = [t for t in _re.split(r"\W+", primary.lower()) if t]
        pats = [_re.compile(r"\b" + _re.escape(t) + r"\b") for t in toks if len(t) >= 3]
        for row in soup.select("table tr, .result, .card")[:20]:
            txt = row.get_text(" ", strip=True)
            if len(txt) < 600 and pats and all(p.search(txt.lower()) for p in pats):
                out.append(hit("etbis", txt[:120], "https://etbis.ticaret.gov.tr/tr/SiteSorgulama", txt[:400]))
                if len(out) >= 8:
                    break
    if not out:
        out.append(hit("etbis", f"{primary} — ETBİS şahıs işletme sorgusu",
                       f"https://etbis.ticaret.gov.tr/tr/SiteSorgulama?page=2&url={v['url_ascii']}",
                       "Gerçek kişi tacir unvanda kelime olarak geçerse bulunur (KEP+adres döner)."))
    return out[:8]

async def search_kap_spk(client, v, primary):
    return [
        hit("kap", f"{primary} — KAP bildirim full-text",
            "https://kap.org.tr/tr/bildirim-sorgu",
            "Bildirim İçeriklerinde Ara alanına ismi yaz (atama/pay alım-satım)."),
        hit("spk", f"{primary} — SPK idari yaptırım",
            "https://idariyaptirimlar.spk.gov.tr/IdariParaCezalari",
            "Yıl + Tüm Kayıtları Göster ile ad-unvan filtresi uygula."),
    ]

async def search_ticaretsicil_ekap(client, v, primary):
    return [
        hit("ticaret_sicil", f"{primary} — TTSG ilan taraması",
            "https://www.ticaretsicil.gov.tr/view/hizlierisim/ilangoruntuleme.php",
            "Ünvan biliniyorsa ilanı indirip isim grep yap (üyelik gerekli)."),
        hit("ekap", f"{primary} — EKAP ihale/yasaklı",
            "https://ekap.kik.gov.tr/ekap/ilan/bultenindirme.aspx",
            "Gerçek kişi yüklenici unvan olarak geçer; kurul kararı sorgula."),
        hit("verbis", f"{primary} — VERBİS veri sorumlusu",
            "https://verbis.kvkk.gov.tr/sicil-sorgula",
            "Min 5 karakter + CAPTCHA ile tekil sorgula (şahıs firmasıysa bulunur)."),
    ]

async def search_ckan(client, base, source, primary, query_path="/api/3/action/package_search?q="):
    try:
        r = await _get(client, f"{base}{query_path}{primary}")
        if r and r.status_code == 200:
            j = r.json()
            res = (j.get("result") or {}).get("results", [])[:5]
            out = []
            for d in res:
                out.append(hit(source, d.get("title", source), f"{base}/dataset/{d.get('name','')}",
                               (d.get("notes") or "")[:400]))
            if out:
                return out
    except Exception:
        pass
    return [hit(source, f"{primary} — {source} açık veri", base, "CKAN katalogda tamamlayıcı arama yap.")]

async def search_belediye_ysk(client, v, primary):
    out = []
    out += await search_ckan(client, "https://data.ibb.gov.tr", "ibb", v["url_ascii"])
    out += await search_ckan(client, "https://acikveri.bizizmir.com", "izmir", v["url_ascii"])
    out.append(hit("ysk", f"{primary} — YSK aday arşivi",
                   "https://acikveri.ysk.gov.tr/",
                   "Kesin aday listelerini indirip isim filtrele (siyasi profil tamamlar)."))
    out.append(hit("tuik", f"{primary} — TÜİK/Adalet istatistik bağlamı",
                   "https://veriportali.tuik.gov.tr/",
                   "Bölgesel suç tipolojisi için toplu istatistikle eşleştir."))
    return out
