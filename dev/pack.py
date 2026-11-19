#!/usr/bin/env python3
"""Assemble le zip à publier : scripts + dossier patch/ déjà fabriqué par vfdelta.py.
Usage : pack.py <dossier patch> <dossier de sortie>"""
import sys, os, json, zipfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
patch, dist = sys.argv[1], sys.argv[2]
M = json.load(open(os.path.join(patch, "manifest.json"), encoding="utf-8"))
top = "NeoJunkCity-FR"
name = f"NeoJunkCity-FR-v{M['patch_version']}-build{M['build']}.zip"
lisezmoi = f"""Neo Junk City - patch français non officiel, version {M['patch_version']}
Pour la version Steam du jeu : build {M['build']}

WINDOWS
  1. Extrayez tout ce zip dans un dossier.
  2. Fermez le jeu, puis double-cliquez sur Installer.bat.
     (Avertissement Windows : Informations complémentaires > Exécuter quand même.)
  3. Dans le jeu, laissez la langue sur English : le texte y est en français.
  Pour revenir en arrière : Desinstaller.bat

LINUX / STEAM DECK
  ./installer-linux.sh        puis, pour revenir en arrière : ./desinstaller-linux.sh

Après une mise à jour du jeu par Steam, il faut la version du patch correspondante.
Traduction faite par une IA : signalez les erreurs sur la page du projet.
Détails, limites connues et nouvelles versions : https://github.com/tonyctalope/NeoJunkCity-FR
""".replace("\n", "\r\n")
os.makedirs(dist, exist_ok=True)
out = os.path.join(dist, name)
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    z.writestr(f"{top}/LISEZMOI.txt", b"\xef\xbb\xbf" + lisezmoi.encode("utf-8"))
    for f in ("Installer.bat", "Desinstaller.bat", "vf.ps1", "installer-linux.sh", "desinstaller-linux.sh", "vf.py", "LICENSE"):
        zi = zipfile.ZipInfo.from_file(os.path.join(ROOT, f), f"{top}/{f}")
        zi.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(zi, open(os.path.join(ROOT, f), "rb").read())
    for f in sorted(os.listdir(patch)):
        z.write(os.path.join(patch, f), f"{top}/patch/{f}", zipfile.ZIP_STORED)
print(out, os.path.getsize(out), "octets,", len(M["files"]), "fichiers de jeu concernés")
