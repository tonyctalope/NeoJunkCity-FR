#!/usr/bin/env python3
"""Essai complet des installateurs sur un faux dossier de jeu (données aléatoires, aucun fichier du jeu).
Sous Windows : essaie vf.ps1 avec Windows PowerShell 5.1, Installer.bat / Desinstaller.bat et vf.py.
Ailleurs : essaie vf.py (et vf.ps1 si pwsh est présent). Usage : selftest.py [dossier de travail]"""
import sys, os, random, shutil, subprocess, hashlib, json, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "dev"))
import vfdelta
WIN = os.name == "nt"
rnd = random.Random(7)


def blob(n):
    return rnd.getrandbits(8 * n).to_bytes(n, "little")


def mutate(b, edits):
    b = bytearray(b)
    for _ in range(edits):
        p = rnd.randrange(len(b)); k = rnd.choice("rid")
        if k == "r": b[p:p + rnd.randrange(1, 400)] = blob(rnd.randrange(1, 400))
        elif k == "i": b[p:p] = blob(rnd.randrange(1, 3000))
        else: del b[p:p + rnd.randrange(1, 3000)]
    return bytes(b)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.isfile(p) else None


def run(cmd, env=None, stdin=subprocess.DEVNULL):
    e = dict(os.environ); e["NJC_NOPAUSE"] = "1"; e.update(env or {})
    r = subprocess.run(cmd, env=e, stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = r.stdout.decode("utf-8", "replace")
    shown = cmd if isinstance(cmd, str) else " ".join(os.path.basename(str(c)) for c in cmd[:6])
    print("   $", shown.encode("ascii", "replace").decode(), "->", r.returncode)
    for l in out.strip().splitlines()[-6:]: print("      |", l.encode("ascii", "replace").decode())
    return r.returncode


def main():
    work = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="vftest")
    work = os.path.join(os.path.abspath(work), "Jeux \u00e0 moi (test)")
    shutil.rmtree(work, ignore_errors=True)
    lib = os.path.join(work, "Biblioth\u00e8que Steam")
    game = os.path.join(lib, "steamapps", "common", "Neo Junk City"); data = os.path.join(game, "Neo Junk City_Data")
    orig = os.path.join(work, "orig"); new1 = os.path.join(work, "new1"); new2 = os.path.join(work, "new2")
    names = {"resources.assets": 9_000_000, "level0": 300_000, "level12": 1_200_000, "sharedassets3.assets": 70_000,
             "StreamingAssets/EmailData.txt": 14_000, "untouched.assets": 50_000}
    for d in (orig, new1, new2):
        os.makedirs(os.path.join(d, "StreamingAssets"))
    for n, size in names.items():
        a = blob(size); open(os.path.join(orig, n), "wb").write(a)
        same = n.startswith("untouched")
        b1 = a if same else mutate(a, 60)
        if n == "level12": b1 = b1[400_000:800_000] + b1[:400_000] + b1[800_000:]     # blocs déplacés
        open(os.path.join(new1, n), "wb").write(b1); open(os.path.join(new2, n), "wb").write(a if same else mutate(b1, 15))
    pkgs = {}
    for v, nd in (("1.0", new1), ("1.1", new2)):
        pkg = os.path.join(work, "Patch FR " + v); os.makedirs(pkg)
        for f in ("vf.py", "vf.ps1", "Installer.bat", "Desinstaller.bat", "installer-linux.sh", "desinstaller-linux.sh"):
            shutil.copy2(os.path.join(ROOT, f), pkg)
        vfdelta.make(orig, nd, os.path.join(pkg, "patch"), "TEST", v)
        pkgs[v] = pkg
    patched = [n for n in names if not n.startswith("untouched")]

    def reset():
        shutil.rmtree(lib, ignore_errors=True)
        for n in names:
            os.makedirs(os.path.dirname(os.path.join(data, n)), exist_ok=True)
            shutil.copyfile(os.path.join(orig, n), os.path.join(data, n))

    def state(ref):
        return all(sha(os.path.join(data, n)) == sha(os.path.join(ref, n)) for n in names)

    tools = {"python": lambda pkg, act, *a: [sys.executable, os.path.join(pkg, "vf.py"), act, *a]}
    ps = ["powershell"] if WIN else (["pwsh"] if shutil.which("pwsh") else None)
    if ps:
        tools["powershell"] = lambda pkg, act, *a: ps + ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", os.path.join(pkg, "vf.ps1"), act, *a]
    if WIN:
        tools["bat"] = lambda pkg, act, *a: 'cmd /s /c "' + " ".join('"%s"' % x for x in (
            os.path.join(pkg, "Installer.bat" if act == "install" else "Desinstaller.bat"), *a)) + '"'
        if shutil.which("pwsh"):
            tools["pwsh7"] = lambda pkg, act, *a: ["pwsh", "-NoProfile", "-File", os.path.join(pkg, "vf.ps1"), act, *a]
    fails = []

    def check(cond, what):
        print("  ", "ok  " if cond else "FAIL", what)
        if not cond: fails.append(what)

    for name, cmd in tools.items():
        print("==", name)
        reset()
        check(run(cmd(pkgs["1.0"], "install", game)) == 0 and state(new1), f"{name}: installation")
        check(all(sha(os.path.join(game, "VF_sauvegarde", n)) == sha(os.path.join(orig, n)) for n in patched), f"{name}: copies de s\u00e9curit\u00e9")
        check(not os.path.exists(os.path.join(data, "_vf_tmp")), f"{name}: dossier temporaire supprim\u00e9")
        check(run(cmd(pkgs["1.0"], "install", game)) == 0 and state(new1), f"{name}: seconde installation sans effet")
        check(run(cmd(pkgs["1.1"], "install", game)) == 0 and state(new2), f"{name}: passage \u00e0 une nouvelle version du patch")
        check(run(cmd(pkgs["1.1"], "uninstall", game)) == 0 and state(orig), f"{name}: d\u00e9sinstallation")
        check(not os.path.exists(os.path.join(game, "VF_sauvegarde")), f"{name}: copies supprim\u00e9es apr\u00e8s d\u00e9sinstallation")
        # dossier _Data donné à la place du dossier du jeu, et installation partielle à terminer
        shutil.copyfile(os.path.join(new1, "level0"), os.path.join(data, "level0"))
        os.makedirs(os.path.join(game, "VF_sauvegarde")); shutil.copyfile(os.path.join(orig, "level0"), os.path.join(game, "VF_sauvegarde", "level0"))
        check(run(cmd(pkgs["1.0"], "install", data)) == 0 and state(new1), f"{name}: reprise d'une installation partielle")
        # jeu mis à jour : un fichier inconnu -> refus sans rien toucher
        reset()
        with open(os.path.join(data, "level12"), "r+b") as f: f.seek(1000); f.write(b"mise a jour")
        before = {n: sha(os.path.join(data, n)) for n in names}
        check(run(cmd(pkgs["1.0"], "install", game)) != 0 and before == {n: sha(os.path.join(data, n)) for n in names}
              and not os.path.exists(os.path.join(game, "VF_sauvegarde")), f"{name}: refus si le jeu n'est pas \u00e0 la bonne version")
        check(run(cmd(pkgs["1.0"], "install", os.path.join(work, "nulle part"))) != 0, f"{name}: dossier inexistant refus\u00e9")
    if WIN and os.environ.get("CI"):
        # détection automatique : faux Steam déclaré dans le registre de la machine d'essai, jeu dans une seconde bibliothèque
        import winreg
        steam = os.path.join(work, "Steam"); os.makedirs(os.path.join(steam, "steamapps"))
        vdf = '"libraryfolders"\n{\n\t"0"\n\t{\n\t\t"path"\t\t"%s"\n\t}\n\t"1"\n\t{\n\t\t"path"\t\t"Q:\\\\absent"\n\t}\n\t"2"\n\t{\n\t\t"path"\t\t"%s"\n\t}\n}\n' % (
            steam.replace("\\", "\\\\"), lib.replace("\\", "\\\\"))
        open(os.path.join(steam, "steamapps", "libraryfolders.vdf"), "w", encoding="utf-8").write(vdf)
        k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
        winreg.SetValueEx(k, "SteamPath", 0, winreg.REG_SZ, steam.replace("\\", "/").lower())
        for name in ("powershell", "bat"):
            reset()
            check(run(tools[name](pkgs["1.0"], "install")) == 0 and state(new1), f"{name}: jeu trouv\u00e9 tout seul via Steam")
            check(run(tools[name](pkgs["1.0"], "uninstall")) == 0 and state(orig), f"{name}: d\u00e9sinstallation sans indiquer le dossier")
        winreg.SetValueEx(k, "SteamPath", 0, winreg.REG_SZ, "c:/nulle/part")
        reset()
        check(run(tools["powershell"](pkgs["1.0"], "install")) != 0 and state(orig), "powershell: jeu introuvable et aucune r\u00e9ponse -> abandon propre")
        # zip non extrait : le .bat seul doit s'expliquer au lieu de planter
        alone = os.path.join(work, "seul"); os.makedirs(alone); shutil.copy2(os.path.join(ROOT, "Installer.bat"), alone)
        check(run('cmd /s /c ""%s""' % os.path.join(alone, "Installer.bat")) == 2, "bat: message clair si le zip n'est pas extrait")
    print("\nR\u00c9SULTAT :", "tout est bon" if not fails else f"{len(fails)} \u00e9chec(s) : {fails}".encode("ascii", "replace").decode())
    shutil.rmtree(work, ignore_errors=True)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
