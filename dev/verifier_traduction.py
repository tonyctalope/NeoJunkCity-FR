#!/usr/bin/env python3
"""Controle la forme des fichiers de traduction/ (lance automatiquement a chaque proposition de modification).
Ne controle pas le sens : seulement que les fichiers restent lisibles par l'outil de construction."""
import sys, os, json, re
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RACINE, "build"))
import textes
T = os.path.join(RACINE, "traduction"); pb = []; vus = {}; total = 0
H = re.compile(r"^[0-9a-f]{8}$")


def caracteres(ou, s):
    s = textes.norm(s)
    m = sorted({c for c in s if ord(c) > 126 and c not in textes.AUTORISES})
    if m: pb.append(f"{ou} : caracteres que le jeu n'affiche pas : {' '.join(m)}")


for f in sorted(os.listdir(os.path.join(T, "dialogues"))):
    if not f.endswith(".jsonl"): continue
    for n, x in enumerate(open(os.path.join(T, "dialogues", f), encoding="utf-8"), 1):
        if not x.strip(): continue
        ou = f"dialogues/{f} ligne {n}"
        try:
            o = json.loads(x)
        except ValueError as e:
            pb.append(f"{ou} : JSON invalide ({e})"); continue
        if sorted(o) != ["fr", "h", "id"] or not isinstance(o["id"], int) or not isinstance(o["fr"], str) or not H.match(str(o["h"])):
            pb.append(f"{ou} : il faut exactement id (nombre), h (8 caracteres, a ne pas modifier) et fr (texte)"); continue
        if o["id"] in vus: pb.append(f"{ou} : id {o['id']} deja present dans {vus[o['id']]}")
        vus[o["id"]] = ou; total += 1
        if not o["fr"].strip(): pb.append(f"{ou} : texte vide (pour revenir a l'anglais, supprimez la ligne)")
        caracteres(ou, o["fr"])
for n, x in enumerate(open(os.path.join(T, "hors_dialogues.jsonl"), encoding="utf-8"), 1):
    if not x.strip(): continue
    ou = f"hors_dialogues.jsonl ligne {n}"
    try:
        o = json.loads(x)
    except ValueError as e:
        pb.append(f"{ou} : JSON invalide ({e})"); continue
    if sorted(o) != ["cls", "fr", "h", "n", "path"] or not isinstance(o["fr"], str) or not H.match(str(o["h"])) or not isinstance(o["n"], int):
        pb.append(f"{ou} : il faut cls, path, n, h (a ne pas modifier) et fr (texte)"); continue
    total += 1
try:
    e = json.load(open(os.path.join(T, "ennemis.json"), encoding="utf-8"))["entries"]
    for i, x in enumerate(e):
        if not isinstance(x.get("key"), str): pb.append(f"ennemis.json entree {i} : champ key manquant")
        for k in ("name", "description"):
            if isinstance(x.get(k), str): caracteres(f"ennemis.json entree {i} ({k})", x[k])
    total += len(e)
except Exception as ex:
    pb.append(f"ennemis.json : illisible ({ex})")
m = open(os.path.join(T, "emails.txt"), encoding="utf-8").read()
for i, x in enumerate([x for x in m.split("<end>") if x.strip()]):
    if x.strip().count(":") < 2: pb.append(f"emails.txt message {i + 1} : il faut cle:objet:texte")
    caracteres(f"emails.txt message {i + 1}", x)
print(f"{total} textes controles, {len(pb)} probleme(s)")
for x in pb[:100]: print("  ", x)
sys.exit(1 if pb else 0)
