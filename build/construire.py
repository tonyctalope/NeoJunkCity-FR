#!/usr/bin/env python3
"""Reconstruit le patch francais a partir du texte de traduction/ et de VOS fichiers du jeu.

    pip install -r build/requirements.txt
    python build/construire.py                 (trouve le jeu via Steam)
    python build/construire.py --jeu "D:\\SteamLibrary\\steamapps\\common\\Neo Junk City"

Resultat : le dossier patch/ a cote des installateurs. Lancez ensuite Installer.bat ou ./installer-linux.sh.
Les fichiers du jeu ne sont pas modifies par ce script : il lit, et ecrit dans le dossier de sortie."""
import sys, os, re, struct, glob, json, argparse, shutil, tempfile
ICI = os.path.dirname(os.path.abspath(__file__)); RACINE = os.path.dirname(ICI)
sys.path.insert(0, ICI); sys.path.insert(0, RACINE); sys.path.insert(0, os.path.join(RACINE, "dev"))
import UnityPy
import unite, textes, enslot, vf

SLOT = 3            # emplacement de l'allemand dans les traductions de chaque ligne (langue n. 4)


def main():
    ap = argparse.ArgumentParser(description="Reconstruit le patch francais de Neo Junk City")
    ap.add_argument("--jeu", help="dossier du jeu (sinon cherche via Steam)")
    ap.add_argument("--traduction", default=os.path.join(RACINE, "traduction"))
    ap.add_argument("--sortie", help="dossier ou ecrire les fichiers traduits complets (sinon dossier temporaire)")
    ap.add_argument("--patch", default=os.path.join(RACINE, "patch"), help="dossier du patch a fabriquer")
    ap.add_argument("--version", default="local", help="nom de version du patch")
    ap.add_argument("--sans-patch", action="store_true", help="ne fabrique que les fichiers traduits (--sortie)")
    a = ap.parse_args()
    game = vf.test_game(a.jeu) if a.jeu else vf.find_game()
    if not game:
        raise SystemExit("Jeu introuvable : indiquez son dossier avec --jeu")
    data = os.path.join(game, vf.DATA); D = os.path.join(data, "")
    unite.config(data)
    sortie = a.sortie or tempfile.mkdtemp(prefix="vf_sortie_")
    os.makedirs(os.path.join(sortie, "StreamingAssets"), exist_ok=True)
    print("Jeu :", game)

    # --- d'ou lire les fichiers d'ORIGINE : le jeu, ou la copie de l'installateur si le patch est deja installe
    sm_pid = unite.script_pid("SpeechManager"); sm_nodes = unite.gen().get_nodes_up("Assembly-CSharp", "AC.SpeechManager")

    def table(env):
        o = next(o for o in env.objects if o.type.name == "MonoBehaviour" and unite.script_ref(o) == sm_pid)
        return o, unite.decode(o.get_raw_data(), sm_nodes, octets=False)
    langue = table(UnityPy.load(D + "resources.assets"))[1]["Languages"][SLOT + 1]["name"]
    deja = langue != "Deutsch"
    bak = os.path.join(game, vf.BACKUP)
    if deja and not os.path.isfile(os.path.join(bak, "resources.assets")):
        raise SystemExit("Le jeu est deja patche et la copie des fichiers d'origine est absente : desinstallez le patch "
                         "ou verifiez l'integrite des fichiers dans Steam, puis relancez.")
    if deja:
        print("Le patch est deja installe : lecture des fichiers d'origine dans", vf.BACKUP)

    def origine(rel):
        b = os.path.join(bak, rel.replace("/", os.sep))
        return b if deja and os.path.isfile(b) else os.path.join(data, rel.replace("/", os.sep))

    # --- 1. table des dialogues
    fr = textes.dialogues(a.traduction)
    env = UnityPy.load(origine("resources.assets"))
    obj, sm = table(env)
    if sm["Languages"][SLOT + 1]["name"] != "Deutsch":
        raise SystemExit("Fichiers d'origine inattendus (langue n. 4 = %r)" % sm["Languages"][SLOT + 1]["name"])
    faites = sans = changees = 0; alertes = []
    id2en = {l["lineID"]: l["text"] for l in sm["lines"]}; final = {}
    for l in sm["lines"]:
        i = l["lineID"]; en = l["text"]; e = fr.get(i)
        if e is not None and e[0] == textes.empreinte(en) and e[1].strip():
            t = textes.norm(e[1])
            if en[-1:] == " " and t[-1:] != " ": t += " "
            if en[:1] == " " and t[:1] != " ": t = " " + t
            for pb in textes.controle(en, t):
                alertes.append(f"ligne {i} : {pb}")
            faites += 1
        else:
            t = textes.norm(en)                 # pas de traduction (ou phrase d'origine modifiee par le jeu) : anglais
            if e is None: sans += 1
            else: changees += 1
        l["translationText"][SLOT] = t; final[i] = t
    sm["Languages"][SLOT + 1]["name"] = "Fran\u00e7ais"
    for l in sm["lines"]:
        l["text"] = final[l["lineID"]]
    obj.set_raw_data(unite.encode(sm, sm_nodes))
    print(f"dialogues : {faites} lignes en francais, {sans} laissees en anglais (pas de traduction), "
          f"{changees} revenues a l'anglais car le jeu a modifie la phrase d'origine")

    # --- 2. images et scenes propres a l'allemand -> celles de l'anglais
    gt_nodes = unite.gen().get_nodes_up("Assembly-CSharp", "GraphicTranslator"); gt_pid = unite.script_pid("GraphicTranslator")
    acl_nodes = unite.gen().get_nodes_up("Assembly-CSharp", "AC.ActionCheckLanguage"); acl_pid = unite.script_pid("ActionCheckLanguage")

    def patch_gfx(e):
        n = 0
        for o in e.objects:
            if o.type.name != "MonoBehaviour" or unite.script_ref(o) != gt_pid: continue
            d = o.read_typetree(gt_nodes); lg = d["languageGraphics"]
            if len(lg) > SLOT + 1 and lg[SLOT + 1]["graphic"] != lg[0]["graphic"]:
                lg[SLOT + 1]["graphic"] = dict(lg[0]["graphic"]); o.save_typetree(d, gt_nodes); n += 1
        return n

    def patch_checks(e, name):
        """Actions "Check Language" enchainees anglais -> ... -> allemand -> ... -> defaut : l'allemand mene ou mene l'anglais."""
        chk = {}
        for o in e.objects:
            if o.type.name != "MonoBehaviour" or unite.script_ref(o) != acl_pid: continue
            chk[o.path_id] = (o, o.read_typetree(acl_nodes))
        n = 0
        for pid, (o, d) in chk.items():
            if d["currentLanguage"] != SLOT + 1 or len(d["endings"]) != 2: continue
            target = None
            for epid, (eo, ed) in chk.items():
                if ed["currentLanguage"] != 0 or len(ed["endings"]) != 2: continue
                cur, seen, hit = ed, set(), False
                while True:                                  # suit les liens "faux" de la chaine
                    nxt = cur["endings"][1]["skipActionActual"]["m_PathID"]
                    if nxt == pid: hit = True
                    if nxt not in chk or nxt in seen: break
                    seen.add(nxt); cur = chk[nxt][1]
                if not hit: continue
                t = ed["endings"][0]
                if t["resultAction"] == 2: target = dict(t)
                elif t["resultAction"] == 0 and cur["endings"][1]["resultAction"] == 2 \
                        and cur["endings"][1]["skipAction"] == ed["endings"][1]["skipAction"] - 1:
                    target = dict(cur["endings"][1])       # "continuer" en anglais = l'action par defaut de la chaine
                break
            if target is None: print("  test de langue non modifie :", name, pid); continue
            if d["endings"][0] != target:
                d["endings"][0] = target; o.save_typetree(d, acl_nodes); n += 1
        return n
    gfx = patch_gfx(env); checks = patch_checks(env, "resources.assets")

    # --- 3. francais a la place de l'anglais dans les champs de texte d'origine
    scan_brut, scan = textes.ennemis(a.traduction)
    ES = enslot.EnSlot(id2en, final, textes.hors_dialogues(a.traduction), scan)
    texts = ES.patch(env, "resources.assets", skip={obj.path_id})
    fontfix = enslot.patch_fonts(env)

    # --- 4. fiches d'ennemis (fichier texte du jeu)
    ta = {o.peek_name(): o for o in env.objects if o.type.name == "TextAsset" and o.peek_name() in ("German", "English")}
    if len(ta) == 2 and scan_brut is not None:
        for k in ("German", "English"):
            x = ta[k].read(); x.m_Script = textes.norm(scan_brut); x.save()
        print("fiches d'ennemis : en francais")
    else:
        print("fiches d'ennemis : non trouvees, laissees telles quelles")

    # --- 5. banniere de victoire : la version allemande prend les lettres de la version anglaise
    _objs = {o.path_id: o for o in env.objects}

    def _tree(gopid, out):
        go = _objs[gopid].read(); tr = None; sr = None
        for c in go.m_Component:
            o = _objs[c.component.m_PathID]
            if o.type.name in ("Transform", "RectTransform"): tr = o.read()
            if o.type.name == "SpriteRenderer": sr = o
        out.append((go.m_Name, sr))
        for ch in tr.m_Children: _tree(_objs[ch.m_PathID].read().m_GameObject.m_PathID, out)
        return out
    _vic = {o.peek_name(): o.path_id for o in env.objects if o.type.name == "GameObject" and o.peek_name() in ("Victory_German", "Victory_English")}
    if len(_vic) == 2:
        x_, y_ = _tree(_vic["Victory_German"], []), _tree(_vic["Victory_English"], [])
        if [x[0] for x in x_[1:]] == [x[0] for x in y_[1:]] and all((x[1] is None) == (y[1] is None) for x, y in zip(x_, y_)):
            for x, y in zip(x_, y_):
                if x[1] is None: continue
                ra, rb = x[1].get_raw_data(), y[1].get_raw_data()
                if len(ra) == len(rb) and ra[12:] != rb[12:]:
                    x[1].set_raw_data(ra[:12] + rb[12:])      # garde seulement le lien vers son objet
    ecrits = ["resources.assets"]
    open(os.path.join(sortie, "resources.assets"), "wb").write(env.file.save())

    # --- 6. e-mails
    ef = os.path.join(a.traduction, "emails.txt")
    if os.path.exists(ef):
        cles = lambda s: [e.strip().split(":")[0] for e in s.split("<end>") if e.strip()]
        txt = textes.norm(open(ef, encoding="utf-8").read())
        if cles(open(origine("StreamingAssets/EmailData.txt"), encoding="utf-8").read()) == cles(txt):
            for n in ("EmailData.txt", "EmailData_DE.txt"):
                open(os.path.join(sortie, "StreamingAssets", n), "w", encoding="utf-8", newline="").write(txt)
                ecrits.append("StreamingAssets/" + n)
            print("e-mails :", len(cles(txt)), "messages")
        else:
            print("e-mails : la liste des messages du jeu a change, e-mails laisses en anglais")

    # --- 7. libelle de la langue sur l'ecran du premier lancement, puis toutes les scenes
    env0 = UnityPy.load(origine("level0")); n0 = 0
    for o in env0.objects:
        raw = o.get_raw_data(); old = struct.pack("<i", 7) + b"Deutsch\x00"
        if o.type.name == "MonoBehaviour" and raw.count(old) == 1:
            new = "Fran\u00e7ais".encode(); new = struct.pack("<i", len(new)) + new + b"\x00" * (-len(new) % 4)
            o.set_raw_data(raw.replace(old, new)); n0 += 1
    for path in sorted(glob.glob(glob.escape(D) + "level*") + glob.glob(glob.escape(D) + "sharedassets*.assets")):
        name = os.path.basename(path)
        if "." in name and not name.endswith(".assets"): continue
        e = env0 if name == "level0" else UnityPy.load(origine(name))
        k = patch_gfx(e); gfx += k
        c = patch_checks(e, name); checks += c; k += c
        c = ES.patch(e, name); texts += c; k += c
        c = enslot.patch_fonts(e); fontfix += c; k += c
        if k or (name == "level0" and n0 == 1):
            open(os.path.join(sortie, name), "wb").write(e.file.save()); ecrits.append(name)
    ids_used = {i for i, e in id2en.items() if e in ES.used}
    need = {i for i in final if final[i] != id2en[i]}
    print(f"texte d'origine : {texts} composants reecrits, {len(ids_used & need)} lignes sur {len(need)} placees")
    print(f"  noms laisses en anglais car le code du jeu s'en sert : {len(ES.kept_literal)}")
    print(f"  polices : {fontfix} elements d'interface passent sur la police qui a les accents")
    print(f"  textes hors table des dialogues : {len(ES.extra_used)} sur {len(ES.extra)} places")
    if ES.skipped: print("  composants ignores :", dict(ES.skipped))
    print(f"images : {gfx} images allemandes remplacees par les anglaises, {checks} tests de langue rediriges, {len(ecrits)} fichiers ecrits")
    if alertes:
        print(f"\n{len(alertes)} ligne(s) a verifier :")
        for x in alertes[:40]: print("  ", x)

    # --- 8. dossier patch/ pour les installateurs
    if not a.sans_patch:
        import vfdelta
        m = None
        acf = os.path.join(os.path.dirname(os.path.dirname(game)), "appmanifest_2378230.acf")
        if os.path.isfile(acf):
            m = re.search(r'"buildid"\s+"(\d+)"', open(acf, encoding="utf-8", errors="replace").read())
        shutil.rmtree(a.patch, ignore_errors=True)
        vfdelta.make(None, sortie, a.patch, m.group(1) if m else "inconnue", a.version, sorted(ecrits), orig_of=origine, verbose=False)
        print("Patch pret dans", a.patch, ": lancez Installer.bat ou ./installer-linux.sh")
    if not a.sortie:
        shutil.rmtree(sortie, ignore_errors=True)
    else:
        print("Fichiers traduits complets dans", sortie)


if __name__ == "__main__":
    main()
