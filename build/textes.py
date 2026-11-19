"""Textes de la traduction : lecture des fichiers de traduction/, normalisation typographique, empreintes."""
import os, re, json, zlib

# Caracteres que les polices du jeu n'affichent pas : remplaces par un equivalent sur.
NORM = {'\u2019': "'", '\u2018': "'", '\u2026': '...', '\u0153': 'oe', '\u0152': 'Oe', '\xab': '"', '\xbb': '"', '\u201c': '"', '\u201d': '"', '\u201e': '"', '\u2013': '-', '\u2014': '-', '\xa0': ' ', '\u202f': ' ', '\u2009': ' '}
AUTORISES = set('\xa1\xb0\xb7\xbf\xc0\xc2\xc4\xc6\xc7\xc8\xc9\xca\xcb\xce\xcf\xd1\xd4\xd6\xd9\xdb\xdc\xdf\xe0\xe1\xe2\xe4\xe6\xe7\xe8\xe9\xea\xeb\xed\xee\xef\xf1\xf3\xf4\xf6\xf9\xfa\xfb\xfc\xff\u20ac')
BALISE = re.compile(r"</?[A-Za-z][^>\n]{0,40}>")
TECH = re.compile(r"\[(?:var|localvar|input|expression|Var|token|paramlabel|paramval|line|wait|speaker|hold|continue):?[^\]\n]*\]|\[button\]|\[\d+\]|\{\d+\}")


def norm(s):
    for a, b in NORM.items():
        s = s.replace(a, b)
    return re.sub(r" +([?!;:])", r" \1", s)   # une seule espace simple avant la ponctuation haute


def empreinte(s):
    """Empreinte de la phrase d'origine (pas le texte lui-meme) : sert a savoir si le jeu l'a modifiee depuis."""
    return "%08x" % (zlib.crc32(s.encode("utf-8")) & 0xffffffff)


def lire_jsonl(chemin):
    out = []
    with open(chemin, encoding="utf-8") as f:
        for n, x in enumerate(f, 1):
            x = x.strip()
            if not x:
                continue
            try:
                out.append(json.loads(x))
            except ValueError as e:
                raise SystemExit(f"{chemin} ligne {n} : JSON invalide ({e})")
    return out


def dialogues(dossier):
    """id -> (empreinte de l'anglais, texte francais)"""
    d = {}
    sous = os.path.join(dossier, "dialogues")
    for f in sorted(os.listdir(sous)):
        if f.endswith(".jsonl"):
            for o in lire_jsonl(os.path.join(sous, f)):
                d[int(o["id"])] = (o["h"], o["fr"])
    return d


def hors_dialogues(dossier):
    """(classe, champ, longueur, empreinte de l'anglais) -> francais, pour les textes hors de la table des dialogues"""
    p = os.path.join(dossier, "hors_dialogues.jsonl"); ex = {}
    if os.path.exists(p):
        for o in lire_jsonl(p):
            f = norm(o["fr"])
            if f:
                ex[(o["cls"], o["path"], int(o["n"]), o["h"])] = f
    return ex


def ennemis(dossier):
    """(texte brut du fichier, nom d'origine -> description francaise)"""
    p = os.path.join(dossier, "ennemis.json")
    if not os.path.exists(p):
        return None, {}
    brut = open(p, encoding="utf-8").read()
    return brut, {e["key"]: norm(e["description"]) for e in json.loads(brut)["entries"] if e.get("description")}


def controle(en, fr):
    """Problemes d'une ligne par rapport a l'originale : balises, jetons techniques, retours a la ligne, caracteres."""
    pb = []
    if sorted(t.lower() for t in BALISE.findall(en)) != sorted(t.lower() for t in BALISE.findall(fr)):
        pb.append("balises <...> differentes de l'original")
    if sorted(TECH.findall(en)) != sorted(TECH.findall(fr)):
        pb.append("jetons techniques [...] differents de l'original")
    if en.count("\n") != fr.count("\n"):
        pb.append("nombre de retours a la ligne different")
    mauvais = sorted({c for c in fr if ord(c) > 126 and c not in AUTORISES})
    if mauvais:
        pb.append("caracteres non affiches par le jeu : " + " ".join(mauvais))
    return pb
