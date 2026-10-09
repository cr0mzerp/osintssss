"""AZ connectorları — açık/kayıtsız sayfalar, best-effort parse."""
from bs4 import BeautifulSoup
from .tr import hit, _get, search_ckan

async def search_etaxes(client, v, primary):
    return [hit("etaxes", f"{primary} — VÖEN/ad araması",
                "https://www.taxes.gov.az/az/page/vergi-odeyicileri-uzre-axtaris",
                "VÖEN və ya ad yaz: fərdi sahibkar + ad-soyad dene, şirket unvanı aynen yazılmalı.")]

async def search_etender(client, v, primary):
    out = [hit("etender", f"{primary} — ihale taraması",
               "https://www.etender.gov.az/",
               "Şirket unvan varyantları (MMC/QSC/ASC) ile ara; şahıs ancak fərdi sahibkar kazandıysa geçer.")]
    return out

async def search_courts(client, v, primary):
    out = []
    r = await _get(client, "https://courts.gov.az/courtCases")
    if r and r.status_code == 200:
        out.append(hit("emehkeme", f"{primary} — courts.gov.az dava/karar listesi",
                       "https://courts.gov.az/courtCases",
                       "məhkəmə + tarih + kategori ile çekip metinde isim varyantlarını lokal grep yap (taraflar anonim)."))
    else:
        out.append(hit("emehkeme", f"{primary} — e-məhkəmə anonim kararlar",
                       "https://e-mehkeme.gov.az/Public/AnonymizeDecisions",
                       "Karar metnini indirip varyantlarla tara, girişli kabinete girme."))
    out.append(hit("supremecourt_az", f"{primary} — Ali Məhkəmə içtihat",
                   "https://supremecourt.gov.az/",
                   "Kişi için değil içtihat için: kateqoriya + alt kateqoriya seç."))
    out.append(hit("eqanun", f"{primary} — e-qanun mevzuat/təltif",
                   "https://e-qanun.az/",
                   "Təltif/əməkdar fərmanlarında isim geçebilir; standart axtarışta dene."))
    return out

async def search_media_whois(client, v, primary):
    return [
        hit("media_reyestri", f"{primary} — Medya Reyestri (Ad, soyad, ata adı)",
            "https://reyestr.media.gov.az/Home/Search",
            "Minimum 5 simvol; ə/ğ doğru yaz, jurnalist/media bağlantısı döner."),
        hit("whois_az", f"{primary} — whois.az domain doğrulama",
            "https://whois.az/",
            "İsimden domaine gidilemez; olası adsoyad.az varyantlarını tek tek sorgula (captcha var)."),
    ]

async def search_mia_prosecutor(client, v, primary):
    out = []
    for url, src in [("https://mia.gov.az/az/news/archive", "mia_az"),
                     ("https://genprosecutor.gov.az/az/page/media/xeberler", "genprosecutor_az")]:
        r = await _get(client, url)
        if r and r.status_code == 200:
            q = primary.lower()
            soup = BeautifulSoup(r.text, "lxml")
            found = 0
            for el in soup.select("a, h3, h2, .news, article")[:60]:
                txt = el.get_text(" ", strip=True)
                if q.split()[0] in txt.lower() and primary.split()[-1].lower()[:4] in txt.lower() and 10 < len(txt) < 300:
                    href = el.get("href", "") if el.name == "a" else ""
                    link = href if href.startswith("http") else url
                    out.append(hit(src, txt[:120], link, txt[:400]))
                    found += 1
                    if found >= 4:
                        break
    if not out:
        out = [
            hit("mia_az", f"{primary} — DİN xəbər arşivi",
                "https://mia.gov.az/az/news/archive",
                "Xəbərlərdə axtar + Google: site:mia.gov.az \"AD SOYAD\"."),
            hit("genprosecutor_az", f"{primary} — Baş Prokurorluq bülten",
                "https://genprosecutor.gov.az/az/page/media/xeberler",
                "Google: site:genprosecutor.gov.az/az/post \"AD SOYAD\"."),
        ]
    return out

async def search_opendata_az(client, v, primary):
    return await search_ckan(client, "https://opendata.az", "opendata_az", v["url_ascii"])
