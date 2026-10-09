"""Birleşik skorlama: isim + şehir + tarih. Kaynaksız alan yok."""
import difflib
import re

SOURCE_TRUST = {
    "terorarananlar": 1.0, "resmigazete": 1.0, "aym": 1.0,
    "yargitay": 1.0, "danistay": 1.0, "uyap_emsal": 1.0,
    "ticaret_sicil": 1.0, "etbis": 1.0, "kap": 1.0, "spk": 1.0,
    "verbis": 1.0, "ekap": 1.0, "ysk": 0.9, "ibb": 0.9,
    "izmir": 0.9, "ankara": 0.9, "tuik": 0.9,
    "etaxes": 1.0, "etender": 1.0, "emehkeme": 1.0,
    "supremecourt_az": 0.9, "eqanun": 0.9, "media_reyestri": 1.0,
    "whois_az": 0.9, "mia_az": 1.0, "genprosecutor_az": 1.0,
    "opendata_az": 0.9,
    "interpol": 1.0, "fbi": 1.0, "opensanctions": 1.0,
    "orcid": 0.9, "openalex": 0.8, "crossref": 0.8,
    "github": 0.9, "crtsh": 0.8, "certs": 0.8, "social_xray": 0.6,
    "web": 0.85, "wikipedia": 0.95, "wikidata": 0.9,
    "bluesky": 0.9, "mastodon": 0.85, "stackoverflow": 0.9,
    "scholar": 0.9, "hackernews": 0.8, "username": 0.9,
    "news_gdelt": 0.9,
    "openlibrary": 0.9, "itunes": 0.8, "npm": 0.85, "crates": 0.85,
    "gleif": 0.95, "archive": 0.8, "crossref": 0.85, "musicbrainz": 0.85,
    "doaj": 0.85, "ietf": 0.9, "sec": 0.95, "worldbank": 0.85, "urlscan": 0.75,
    "nih": 0.9, "usaspending": 0.9, "dailymotion": 0.8, "peertube": 0.75,
    "lemmy": 0.8, "packagist": 0.8, "nuget": 0.8, "maven": 0.8, "gbooks": 0.85,
    "web_pro": 0.85, "domains": 0.7,
}

def _tokens(s: str) -> list[str]:
    return [t for t in re.split(r"[^a-zçğıöşüə0-9]+", s.lower()) if t]

COMPANY_PAT = re.compile(r"şirket|ltd|limited|anonim|a\.ş|ticaret|sigorta|matbaa|sulama|holding|grup|market|shop|store|app\b|banka|üniversite|university|hospital|hastane", re.I)
EVENT_PAT = re.compile(r"suikast|deprem|seçim|festival|konser|turnuva|şampiyona|savaşı|operasyonu|davası|olayı", re.I)

def classify(title: str, source: str) -> str:
    if source in ("gleif", "etbis") or COMPANY_PAT.search(title or ""):
        return "company"
    if EVENT_PAT.search(title or "") or " — " in (title or "") and any(
            k in (title or "").lower() for k in ("suikast", "olayı", "davası")):
        return "event"
    if source in ("npm", "crates", "archive") and " — " in (title or ""):
        return "artifact"
    return "person"

def name_score(query: str, hit_title: str) -> float:
    if not query or not hit_title:
        return 0.0
    q = query.lower().strip()
    t = hit_title.lower().strip()
    if q == t:
        return 1.0
    qt, tt = _tokens(query), set(_tokens(hit_title))
    if not qt:
        return 0.0
    exact = sum(1 for tok in qt if tok in tt)
    # tek kelimelik sorgu: kelime olarak geçmiyorsa eşleşme yok
    if len(qt) == 1:
        if qt[0] in tt:
            return 0.95 if len(tt) <= 4 else 0.85
        # handle/login bitişik yazımları: aday handle listesindeyse üst katman bakar
        compact = re.sub(r"\W+", "", t)
        if qt[0] == compact or compact in (qt[0] + "s",):
            return 0.9
        return round(min(difflib.SequenceMatcher(None, q, t).ratio() * 0.5, 0.5), 3)
    # çok kelimeli: tüm kelimeler kelime olarak geçmeli
    if exact == len(qt):
        return 1.0 if len(tt) <= len(qt) + 2 else 0.9
    if exact >= len(qt) - 1 and len(qt) >= 3:
        return 0.75
    # soyad tutuyorsa kısmi kredi
    if len(qt) >= 2 and qt[-1] in tt:
        return 0.6
    return round(min(difflib.SequenceMatcher(None, q, t).ratio() * 0.5, 0.5), 3)

def score_hit(query: str, hit: dict, city_hint: str = "") -> dict:
    ns = name_score(query, hit.get("title", ""))
    trust = SOURCE_TRUST.get(hit.get("source", ""), 0.6)
    final = round(ns * trust, 3)
    title = hit.get("title", "")
    qt = _tokens(query)
    tt = set(_tokens(title))
    matched = [t for t in qt if t in tt]
    hit["why"] = f"eşleşen kelime: {', '.join(matched) or 'yok'} ({len(matched)}/{len(qt)})"
    hit["etype"] = classify(title, hit.get("source", ""))
    if hit.get("kind") == "guide" or (" — " in title and title.startswith(query.split()[0][:4] if query else "___")):
        final = min(final, 0.55)
        hit["kind"] = "guide"
    else:
        hit.setdefault("kind", "finding")
        if hit.get("disambig"):
            final = min(final, 0.65)
        # kullanıcı adı / sertifika varlıkla skorlanır (isim benzerliği aranmaz)
        if hit.get("source") in ("username", "certs", "github", "domains"):
            final = max(final, 0.65)
    level = "hit" if final >= 0.85 else ("candidate" if final >= 0.60 else "weak")
    hit["score"] = final
    hit["level"] = level
    hit["name_sim"] = ns
    return hit

def _core_name(title: str) -> str:
    t = re.sub(r"\(.*?\)", "", title or "")
    t = re.split(r"—|-|·|\|", t)[0]
    return " ".join(_tokens(t)[:4])

def merge_profile(query: str, hits: list[dict]) -> dict:
    findings = [h for h in hits if h.get("kind") != "guide"]
    guides = [h for h in hits if h.get("kind") == "guide"]
    # doğrulama: aynı çekirdek isim ≥2 farklı kaynakta geçmeli, yoksa hit->candidate
    by_core: dict[str, set] = {}
    for h in findings:
        by_core.setdefault(_core_name(h.get("title", "")), set()).add(h.get("source", ""))
    for h in findings:
        if h.get("level") == "hit" and len(by_core.get(_core_name(h.get("title", "")), set())) < 2:
            # wikipedia tam isabet tek başına güçlüyse koru
            if not (h.get("source") == "wikipedia" and h.get("name_sim") == 1.0):
                h["level"] = "candidate"
                h["score"] = min(h.get("score", 0), 0.84)
                h["why"] = (h.get("why", "") + "; tek kaynak — doğrulanmadı")
    good = [h for h in findings if h.get("score", 0) >= 0.60]
    good.sort(key=lambda h: h.get("score", 0), reverse=True)
    names = []
    seen = set()
    for h in good:
        t = h.get("title", "")
        if t and t.lower() not in seen:
            names.append(t)
            seen.add(t.lower())
    conf = round(sum(h.get("score", 0) for h in good) / len(good), 3) if good else 0.0
    warn = None
    if len(query.split()) < 2:
        warn = "Tek kelime sorgu: sonuçlar güvenilmez. Ad + soyad yazın (örn. Talat Yılmaz)."
    # kümeleme: kişi bulgularını ortak bağlam kelimesine göre grupla (olası farklı kişiler)
    qt = set(_tokens(query))
    clusters: dict[str, list] = {}
    for h in good:
        if h.get("etype") not in ("person", None) and h.get("etype") != "person":
            continue
        ctx = [t for t in _tokens(h.get("title", "") + " " + h.get("evidence_snippet", "")) if t not in qt and len(t) >= 4]
        key = None
        for tok, members in clusters.items():
            mtoks = set()
            for m in members:
                mtoks.update(t for t in _tokens(m.get("title", "") + " " + m.get("evidence_snippet", "")) if t not in qt and len(t) >= 4)
            if set(ctx) & mtoks:
                key = tok
                break
        if key is None:
            key = ctx[0] if ctx else "bağlamsız"
        clusters.setdefault(key, []).append(h)
    people = [{"label": k, "count": len(v),
               "top": v[0].get("title", "")[:80],
               "sources": sorted({x.get("source", "") for x in v})[:5]} for k, v in clusters.items()]
    people.sort(key=lambda p: -p["count"])
    etypes: dict[str, int] = {}
    for h in findings:
        etypes[h.get("etype", "person")] = etypes.get(h.get("etype", "person"), 0) + 1
    if len(people) >= 3 and len(query.split()) < 2:
        warn = (warn + " " if warn else "") + f"{len(people)} farklı profile dağılıyor — soyad + şehir ekleyin."
    return {
        "query": query,
        "confidence": conf,
        "warning": warn,
        "names": names[:10],
        "total_hits": len(findings),
        "manual_checks": len(guides),
        "strong": len([h for h in findings if h.get("level") == "hit"]),
        "candidates": len([h for h in findings if h.get("level") == "candidate"]),
        "sources_ok": sorted({h.get("source", "") for h in findings}),
        "etypes": etypes,
        "people": people[:8],
    }
