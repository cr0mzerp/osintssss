"""TR/AZ isim varyant üretici. Tek giriş -> ~10 varyant."""
import re
import urllib.parse

FOLD_MAP = str.maketrans({
    "Ə": "E", "ə": "e",
    "Ş": "S", "ş": "s",
    "Ğ": "G", "ğ": "g",
    "Ç": "C", "ç": "c",
    "Ö": "O", "ö": "o",
    "Ü": "U", "ü": "u",
    "İ": "I", "ı": "i",
    "X": "H", "x": "h",
})

def fold(s: str) -> str:
    return s.translate(FOLD_MAP)

def normalize(s: str) -> str:
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    return s

def translit_pairs(s: str) -> list[str]:
    out = {s}
    pairs = [("Ş", "SH"), ("ş", "sh"), ("Ç", "CH"), ("ç", "ch"),
             ("Ğ", "G"), ("ğ", "g"), ("Ə", "A"), ("ə", "a"),
             ("X", "KH"), ("x", "kh"), ("Q", "G"), ("q", "g")]
    for a, b in pairs:
        if a in s:
            out.add(s.replace(a, b))
    return list(out)

def build_variants(full_name: str) -> dict:
    name = normalize(full_name)
    if not name:
        return {"primary": "", "ascii": "", "quoted": "", "all": [], "blocking_key": ""}
    ascii_fold = fold(name)
    parts = name.split()
    variants = set()
    variants.add(name)
    variants.add(ascii_fold)
    variants.add(name.lower())
    variants.add(ascii_fold.lower())
    for v in list(variants):
        variants.update(translit_pairs(v))
    # bitişik versiyon (domain/kullanıcı adı tahmini)
    nospace = re.sub(r"\s+", "", ascii_fold.lower())
    variants.add(nospace)
    # ters sıra (soyad ad)
    if len(parts) == 2:
        variants.add(f"{parts[1]} {parts[0]}")
        variants.add(f"{fold(parts[1])} {fold(parts[0])}")
        # başharfli
        variants.add(f"{parts[0][0]}. {parts[1]}")
        variants.add(f"{parts[0]} {parts[1][0]}.")
    # oğlu/qızı eklerini temizle (AZ)
    cleaned = re.sub(r"\s+(oğlu|oglu|qızı|qizi|kızı)\b", "", name, flags=re.I)
    if cleaned != name:
        variants.add(cleaned)
        variants.add(fold(cleaned))
    all_v = sorted({v for v in variants if len(v) >= 2}, key=len, reverse=True)[:15]
    surname = parts[-1] if parts else ""
    blocking_key = (fold(surname).lower() + "|" + (fold(parts[0])[0].lower() if parts else ""))
    return {
        "primary": name,
        "ascii": ascii_fold,
        "quoted": f'"{name}"',
        "url": urllib.parse.quote(name),
        "url_ascii": urllib.parse.quote(ascii_fold),
        "all": all_v,
        "blocking_key": blocking_key,
    }
