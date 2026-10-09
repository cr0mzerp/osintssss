"""Kullanıcı adı枚举: isimden aday handle üret, ~14 sitede varlık kontrolü.
Sadece 200+marker = var. 404/timeout = sessiz geç (gürültü yok)."""
import asyncio
import re

SEM = asyncio.Semaphore(8)

def candidates_for(name: str) -> list[str]:
    ascii_fold = name.translate(str.maketrans({
        "Ə": "E", "ə": "e", "Ş": "S", "ş": "s", "Ğ": "G", "ğ": "g",
        "Ç": "C", "ç": "c", "Ö": "O", "ö": "o", "Ü": "U", "ü": "u",
        "İ": "I", "ı": "i", "X": "H", "x": "h"}))
    parts = re.sub(r"[^a-zA-Z ]", "", ascii_fold).lower().split()
    if not parts:
        return []
    first, last = parts[0], parts[-1] if len(parts) > 1 else ""
    c = set()
    if last:
        c.update([first + last, first + "." + last, first + "_" + last,
                  first[0] + last, first + last[0]])
    c.add(first + (last[:4] if last else ""))
    return sorted({x for x in c if 3 <= len(x) <= 30})[:6]

async def _check(client, method, url, must_contain=None, must_absent=None, api_json=None):
    async with SEM:
        try:
            if method == "api":
                r = await client.get(url, timeout=6.0,
                                     headers={"User-Agent": "OSINT-Platform/1.0", "Accept": "application/json"},
                                     follow_redirects=True)
                if r.status_code != 200:
                    return None
                if api_json and not api_json(r):
                    return None
                return True
            r = await client.get(url, timeout=6.0,
                                 headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
                                 follow_redirects=True)
            if r.status_code != 200:
                return None
            txt = r.text
            if must_absent and must_absent in txt:
                return None
            if must_contain and must_contain not in txt:
                return None
            return True
        except Exception:
            return None

def _kb_exact(r, u):
    try:
        them = r.json().get("them") or []
        for t in them:
            if isinstance(t, dict) and ((t.get("basics") or {}).get("username", "").lower() == u.lower()):
                return True
    except Exception:
        pass
    return False

async def check_user(client, u: str) -> list[dict]:
    jobs = [
        ("github", "api", f"https://api.github.com/users/{u}", None, None, lambda r: bool(r.json().get("login"))),
        ("gitlab", "page", f"https://gitlab.com/{u}", u, "429", None),
        ("medium", "page", f"https://medium.com/@{u}", "@" + u, "404", None),
        ("devto", "page", f"https://dev.to/{u}", u, "404", None),
        ("pypi", "page", f"https://pypi.org/user/{u}/", u, "404", None),
        ("rubygems", "page", f"https://rubygems.org/profiles/{u}", u, "couldn't find", None),
        ("dockerhub", "api", f"https://hub.docker.com/v2/users/{u}/", None, None, lambda r: bool(r.json().get("username"))),
        ("keybase", "api", f"https://keybase.io/_/api/1.0/user/lookup.json?usernames={u}", None, None,
         lambda r, u=u: _kb_exact(r, u)),
        ("codeberg", "api", f"https://codeberg.org/api/v1/users/{u}", None, None, lambda r: "message" not in r.json()),
        ("lichess", "api", f"https://lichess.org/api/user/{u}", None, None, lambda r: bool(r.json().get("id"))),
        ("huggingface", "page", f"https://huggingface.co/{u}", u, "404", None),
        ("codepen", "page", f"https://codepen.io/{u}", u, "404", None),
        ("npm", "page", f"https://www.npmjs.com/~{u}", u, "404", None),
        ("chesscom", "page", f"https://www.chess.com/member/{u}", u, "Page Not Found", None),
        ("telegram", "page", f"https://t.me/s/{u}", "tgme_page_title", "If you have <strong>Telegram</strong>, you can contact", None),
        ("bitbucket", "api", f"https://api.bitbucket.org/2.0/users/{u}", None, None, lambda r: bool(r.json().get("display_name"))),
        ("steam", "page", f"https://steamcommunity.com/id/{u}", u, "could not be found", None),
        ("tiktok", "page", f"https://www.tiktok.com/@{u}", u, "Couldn't find this account", None),
        ("pinterest", "page", f"https://www.pinterest.com/{u}/", u, "User not found", None),
        ("youtube", "page", f"https://www.youtube.com/@{u}", u, None, None),
    ]
    profile_url = {
        "github": f"https://github.com/{u}", "gitlab": f"https://gitlab.com/{u}",
        "medium": f"https://medium.com/@{u}", "devto": f"https://dev.to/{u}",
        "pypi": f"https://pypi.org/user/{u}/", "rubygems": f"https://rubygems.org/profiles/{u}",
        "dockerhub": f"https://hub.docker.com/u/{u}", "keybase": f"https://keybase.io/{u}",
        "lichess": f"https://lichess.org/@/{u}", "huggingface": f"https://huggingface.co/{u}",
        "codepen": f"https://codepen.io/{u}", "npm": f"https://www.npmjs.com/~{u}",
        "chesscom": f"https://www.chess.com/member/{u}", "telegram": f"https://t.me/{u}",
        "bitbucket": f"https://bitbucket.org/{u}/", "codeberg": f"https://codeberg.org/{u}",
        "steam": f"https://steamcommunity.com/id/{u}", "tiktok": f"https://www.tiktok.com/@{u}",
        "pinterest": f"https://www.pinterest.com/{u}/", "youtube": f"https://www.youtube.com/@{u}",
    }
    results = await asyncio.gather(*[_check(client, m, url, mc, ma, aj) for _, m, url, mc, ma, aj in jobs])
    out = []
    for (site, *_), ok in zip(jobs, results):
        if ok:
            out.append({"source": "username", "title": f"@{u} — {site} hesabı var",
                        "source_url": profile_url[site],
                        "evidence_snippet": f"'{u}' handle'i {site}'da kayıtlı (profil sayfası açılıyor).",
                        "kind": "finding", "handle": u, "network": site})
    return out

async def search_usernames(client, variants, primary):
    out = []
    for u in candidates_for(primary):
        try:
            hits = await asyncio.wait_for(check_user(client, u), timeout=30.0)
            out.extend(hits)
        except Exception:
            continue
    return out[:24]

async def search_domains(client, variants, primary):
    """Kişisel domain izi: adsoyad varyantları DNS'te çözülüyor mu?"""
    import socket
    out = []
    cands = set()
    for v in variants.get("all", [])[:8]:
        flat = re.sub(r"\W+", "", v.lower())
        if 4 <= len(flat) <= 30:
            cands.add(flat)
    doms = [f"{c}.{tld}" for c in list(cands)[:6] for tld in ("com", "com.tr", "az", "net")][:24]

    def resolve(d):
        try:
            socket.setdefaulttimeout(4)
            socket.gethostbyname(d)
            return True
        except Exception:
            return False

    for d in doms:
        try:
            ok = await asyncio.wait_for(asyncio.to_thread(resolve, d), timeout=5.0)
        except Exception:
            ok = False
        if ok:
            out.append({"source": "domains", "title": f"{d} — kayıtlı domain",
                        "source_url": f"http://{d}",
                        "evidence_snippet": f"'{d}' DNS'te çözülüyor (domain alınmış). Sahibi crt.sh/RDAP ile doğrulanmalı.",
                        "kind": "finding"})
            if len(out) >= 5:
                break
    return out
