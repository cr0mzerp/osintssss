"""Tüm connector kayıtları — tek kutu hepsine fan-out yapar."""
import asyncio
import httpx
from .tr import (search_terorarananlar, search_resmigazete, search_aym,
                 search_yargitay, search_danistay, search_uyap_emsal,
                 search_etbis, search_kap_spk, search_ticaretsicil_ekap,
                 search_belediye_ysk)
from .az import (search_etaxes, search_etender, search_courts,
                 search_media_whois, search_mia_prosecutor, search_opendata_az)
from .global_sources import (search_interpol, search_fbi, search_opensanctions,
                             search_academic, search_tech)
from .real import (search_ddg, search_ddg_pro, search_wiki, search_bsky, search_mastodon,
                   search_github, search_stack, search_semantic, search_hn,
                   search_crtsh, search_gdelt)
from .expand import (search_openlibrary, search_itunes, search_npm, search_crates,
                     search_gleif, search_archive, search_crossref, search_musicbrainz)
from .expand2 import (search_doaj, search_ietf, search_sec, search_worldbank,
                      search_urlscan, search_nih, search_usaspending, search_dailymotion,
                      search_peertube, search_lemmy, search_packagist, search_nuget,
                      search_maven, search_gbooks)
from .usernames import search_usernames, search_domains

# (isim, fonksiyon, kademe) — kademe: t0 hızlı / t1 orta / t2 yavaş
REGISTRY = [
    ("terorarananlar", search_terorarananlar, "t0"),
    ("interpol", search_interpol, "t0"),
    ("fbi", search_fbi, "t0"),
    ("resmigazete", search_resmigazete, "t0"),
    ("etbis", search_etbis, "t0"),
    ("opensanctions", search_opensanctions, "t0"),
    ("kap_spk", search_kap_spk, "t0"),
    ("ticaret_ekap", search_ticaretsicil_ekap, "t0"),
    ("etaxes", search_etaxes, "t0"),
    ("etender", search_etender, "t1"),
    ("aym", search_aym, "t1"),
    ("yargitay", search_yargitay, "t1"),
    ("danistay", search_danistay, "t1"),
    ("uyap_emsal", search_uyap_emsal, "t1"),
    ("courts_az", search_courts, "t1"),
    ("media_whois", search_media_whois, "t1"),
    ("mia_prosecutor", search_mia_prosecutor, "t1"),
    ("opendata_az", search_opendata_az, "t1"),
    ("belediye_ysk", search_belediye_ysk, "t2"),
    ("academic", search_academic, "t2"),
    ("tech", search_tech, "t2"),
    ("web_ddg", search_ddg, "t0"),
    ("web_pro", search_ddg_pro, "t1"),
    ("wiki", search_wiki, "t0"),
    ("bsky", search_bsky, "t1"),
    ("mastodon", search_mastodon, "t1"),
    ("github", search_github, "t1"),
    ("stack", search_stack, "t2"),
    ("scholar", search_semantic, "t1"),
    ("hn", search_hn, "t2"),
    ("certs", search_crtsh, "t2"),
    ("news", search_gdelt, "t2"),
    ("usernames", search_usernames, "t2"),
    ("domains", search_domains, "t2"),
    ("books", search_openlibrary, "t2"),
    ("music", search_itunes, "t2"),
    ("musicbrainz", search_musicbrainz, "t2"),
    ("code", search_npm, "t2"),
    ("crates", search_crates, "t2"),
    ("lei", search_gleif, "t1"),
    ("archive", search_archive, "t2"),
    ("papers", search_crossref, "t2"),
    ("doaj", search_doaj, "t2"),
    ("ietf", search_ietf, "t2"),
    ("sec", search_sec, "t1"),
    ("worldbank", search_worldbank, "t2"),
    ("urlscan", search_urlscan, "t2"),
    ("nih", search_nih, "t2"),
    ("usaspending", search_usaspending, "t2"),
    ("video_dm", search_dailymotion, "t2"),
    ("video_pt", search_peertube, "t2"),
    ("lemmy", search_lemmy, "t2"),
    ("packagist", search_packagist, "t2"),
    ("nuget", search_nuget, "t2"),
    ("maven", search_maven, "t2"),
    ("gbooks", search_gbooks, "t2"),
]

TIMEOUTS = {"t0": 5.0, "t1": 8.0, "t2": 10.0}

async def run_one(name, fn, tier, client, variants, primary):
    try:
        coro = fn(client, variants, primary)
        hits = await asyncio.wait_for(coro, timeout=TIMEOUTS[tier])
        return name, hits or [], None
    except asyncio.TimeoutError:
        return name, [], "timeout"
    except Exception as e:
        return name, [], str(e)[:120]

async def fanout(variants, primary, on_batch=None):
    all_hits, errors = [], {}
    async with httpx.AsyncClient(follow_redirects=True) as client:
        for tier in ["t0", "t1", "t2"]:
            batch = [(n, f) for (n, f, t) in REGISTRY if t == tier]
            results = await asyncio.gather(*[run_one(n, f, tier, client, variants, primary) for n, f in batch])
            for name, hits, err in results:
                all_hits.extend(hits)
                if err:
                    errors[name] = err
            if on_batch:
                await on_batch(tier, all_hits, errors)
    return all_hits, errors
