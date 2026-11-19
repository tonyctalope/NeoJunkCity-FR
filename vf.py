#!/usr/bin/env python3
"""Patch français non officiel de Neo Junk City - installation / désinstallation (Linux, Steam Deck).
Usage : vf.py install|uninstall [dossier du jeu]
Aucune dépendance : Python 3 standard. Ne contient aucun fichier du jeu."""
import sys, os, json, hashlib, zlib, struct, shutil, re

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = "Neo Junk City"
DATA = "Neo Junk City_Data"
BACKUP = "VF_sauvegarde"
TMP = "_vf_tmp"


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def apply_patch(src_path, patch_path, out_path):
    """Format VFP1 : 'VFP1' puis flux deflate brut : int32 nombre d'opérations, puis pour chacune
    0 + int64 position + int32 longueur (copie depuis le fichier d'origine) ou 1 + int32 longueur + octets."""
    with open(patch_path, "rb") as f:
        if f.read(4) != b"VFP1":
            raise ValueError("fichier de patch invalide : " + patch_path)
        ops = zlib.decompress(f.read(), -15)
    pos = 4
    (n,) = struct.unpack_from("<i", ops, 0)
    with open(src_path, "rb") as src, open(out_path, "wb") as out:
        for _ in range(n):
            if ops[pos] == 0:
                off, ln = struct.unpack_from("<qi", ops, pos + 1); pos += 13
                src.seek(off)
                while ln > 0:
                    b = src.read(min(ln, 1 << 20))
                    if not b:
                        raise ValueError("fichier d'origine trop court")
                    out.write(b); ln -= len(b)
            else:
                (ln,) = struct.unpack_from("<i", ops, pos + 1); pos += 5
                out.write(ops[pos:pos + ln]); pos += ln


def test_game(d):
    if not d:
        return None
    d = os.path.expanduser(d.strip().strip('"').strip("'"))
    for c in (d, os.path.join(d, GAME), os.path.dirname(d.rstrip("/\\"))):
        if c and os.path.isfile(os.path.join(c, DATA, "resources.assets")):
            return os.path.abspath(c)
    return None


def find_game():
    home = os.path.expanduser("~")
    roots = [os.path.join(home, p) for p in (".local/share/Steam", ".steam/steam", ".steam/root",
             ".var/app/com.valvesoftware.Steam/.local/share/Steam", "snap/steam/common/.local/share/Steam",
             "Library/Application Support/Steam")]
    roots += [r"C:\Program Files (x86)\Steam"]
    libs = []
    for r in roots:
        libs.append(r)
        vdf = os.path.join(r, "steamapps", "libraryfolders.vdf")
        if os.path.isfile(vdf):
            txt = open(vdf, encoding="utf-8", errors="replace").read()
            libs += [m.replace("\\\\", "\\") for m in re.findall(r'"path"\s+"([^"]+)"', txt)]
    for l in libs:
        g = test_game(os.path.join(l, "steamapps", "common", GAME))
        if g:
            return g
    return test_game(os.path.dirname(HERE)) or test_game(HERE)


def running():
    try:
        for p in os.listdir("/proc"):
            if p.isdigit() and int(p) != os.getpid():
                try:
                    cmd = open(f"/proc/{p}/cmdline", "rb").read()
                except OSError:
                    continue
                if b"Neo Junk City.exe" in cmd:
                    return True
    except OSError:
        pass
    return False


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "install"
    if action not in ("install", "uninstall"):
        print(__doc__); return 2
    mp = os.path.join(HERE, "patch", "manifest.json")
    if not os.path.isfile(mp):
        print("Dossier 'patch' introuvable à côté de ce script : extrayez tout le zip dans un même dossier."); return 2
    M = json.load(open(mp, encoding="utf-8"))
    game = test_game(sys.argv[2]) if len(sys.argv) > 2 else find_game()
    if len(sys.argv) > 2 and not game:
        print("Jeu introuvable dans :", sys.argv[2]); return 1
    while not game:
        print("Jeu introuvable automatiquement.")
        print("Dans Steam : clic droit sur le jeu > Gérer > Parcourir les fichiers locaux, puis collez ici le chemin du dossier.")
        try:
            ans = input("Dossier du jeu (vide pour abandonner) : ")
        except EOFError:
            ans = ""
        if not ans.strip():
            print("Abandon, rien n'a été modifié."); return 1
        game = test_game(ans)
    print(f"Patch français {M.get('patch_version', '?')} pour la version {M['build']} du jeu")
    print("Jeu :", game)
    if running():
        print("Le jeu est en cours d'exécution : fermez-le puis relancez."); return 1
    data = os.path.join(game, DATA); bak = os.path.join(game, BACKUP)
    files = M["files"]

    def paths(f):
        rel = f["path"].replace("/", os.sep)
        return os.path.join(data, rel), os.path.join(bak, rel)

    print(f"Vérification de {len(files)} fichiers...")
    if action == "uninstall":
        todo = []; odd = []
        for f in files:
            cur, b = paths(f)
            h = sha(cur) if os.path.isfile(cur) else None
            if h == f["orig_sha256"]:
                continue
            if h == f["new_sha256"] and os.path.isfile(b) and sha(b) == f["orig_sha256"]:
                todo.append((cur, b))
            else:
                odd.append(f["path"])
        for cur, b in todo:
            shutil.copyfile(b, cur)
        print(f"{len(todo)} fichiers remis dans leur état d'origine.")
        if odd:
            print(f"{len(odd)} fichiers n'ont pas pu être remis (version différente ou copie absente) :", ", ".join(odd[:8]))
            print("Pour tout remettre d'origine : Steam > clic droit sur le jeu > Propriétés > Fichiers installés > Vérifier l'intégrité.")
            return 1
        shutil.rmtree(bak, ignore_errors=True)
        print("Désinstallation terminée.")
        return 0

    plan = []; bad = []; done = 0
    for f in files:
        cur, b = paths(f)
        h = sha(cur) if os.path.isfile(cur) else None
        if h == f["new_sha256"]:
            done += 1
        elif h == f["orig_sha256"]:
            plan.append((f, cur, b, cur))
        elif os.path.isfile(b) and sha(b) == f["orig_sha256"]:
            plan.append((f, cur, b, b))
        else:
            bad.append(f["path"])
    if bad:
        print(f"{len(bad)} fichiers ne correspondent pas à la version {M['build']} du jeu :", ", ".join(bad[:8]))
        print("Le jeu a sans doute été mis à jour (ou modifié par autre chose). Rien n'a été modifié.")
        print("Récupérez la dernière version du patch, ou vérifiez l'intégrité des fichiers dans Steam puis relancez.")
        return 1
    if not plan:
        print("Le patch est déjà installé. Dans le jeu : Options > Language > English."); return 0
    need = sum(f["new_size"] + (f["orig_size"] if src == cur else 0) for f, cur, b, src in plan)
    free = shutil.disk_usage(game).free
    if free < need + (50 << 20):
        print(f"Espace disque insuffisant : il faut environ {need >> 20} Mo libres."); return 1
    for f, cur, b, src in plan:                      # 1. copie de sécurité des originaux
        if src == cur:
            os.makedirs(os.path.dirname(b), exist_ok=True)
            shutil.copyfile(cur, b)
    tmp = os.path.join(data, TMP)
    shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
    placed = 0
    try:
        print(f"Application du patch ({len(plan)} fichiers)...")
        outs = []
        for n, (f, cur, b, src) in enumerate(plan):   # 2. tout est préparé et contrôlé à part
            o = os.path.join(tmp, str(n))
            apply_patch(b, os.path.join(HERE, "patch", f["patch"]), o)
            if sha(o) != f["new_sha256"]:
                raise ValueError("résultat inattendu pour " + f["path"])
            outs.append((o, cur))
        for o, cur in outs:                           # 3. puis mis en place
            os.replace(o, cur); placed += 1
    except Exception as e:
        print("Erreur :", e)
        print("Rien n'a été modifié dans le jeu." if not placed else
              "L'installation s'est arrêtée en cours de route : relancez-la, elle reprendra où elle en était.")
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("Patch français installé.")
    print("Dans le jeu : Options > Language > English (le texte y est en français).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
