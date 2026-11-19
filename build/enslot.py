"""Francais a la place de l'anglais : ecrit le texte francais la ou le jeu garde son texte d'ORIGINE (anglais),
pour que le jeu regle sur English affiche le francais et que tout ce qui n'est pas couvert reste en anglais.
Seuls les champs connus pour etre du texte affiche sont touches (voir FIELDS) ; les identifiants sont laisses."""
import os, collections
import unite as tt, textes
# (class, field path) of display-text fields: replaced when the value is exactly the English text of a line
FIELDS = {
 ("ActionSpeech", ".messageText"), ("CustomUIText", ".text"),
 ("ActionNarratorMessage", ".MessageText"), ("ActionSystemMessage", ".MessageText"),
 ("Conversation", ".options[].label"), ("Conversation", ".selectedOption.label"),
 ("InventoryManager", ".objectives[].title"), ("InventoryManager", ".objectives[].description"),
 ("InventoryManager", ".objectives[].states[].label"), ("InventoryManager", ".objectives[].states[].description"),
 ("InventoryManager", ".objectiveStateActiveLabel.label"), ("InventoryManager", ".objectiveStateCompleteLabel.label"),
 ("InventoryManager", ".objectiveStateFailLabel.label"),
 ("InventoryManager", ".items[].hotspotPrefix1.label"), ("InventoryManager", ".items[].hotspotPrefix2.label"),
 ("InventoryManager", ".items[].altLabel"),
 ("StorePopup", ".currencies[].word"), ("WorldMapAreaFile", ".areas[].markers[].text"),
 ("FailState_SO", ".englishText"),
 ("MenuButton", "._label"), ("MenuLabel", "._label"), ("MenuSlider", ".label"), ("MenuToggle", ".label"),
 ("MenuCycle", ".label"), ("MenuInput", ".label"), ("MenuJournal", ".pages[].text"), ("MenuSavesList", ".newSaveText"),
 ("CursorManager", ".cursorIcons[].label"), ("CursorManager", ".hotspotPrefix1.label"), ("CursorManager", ".hotspotPrefix2.label"),
 ("CursorManager", ".hotspotPrefix3.label"), ("CursorManager", ".hotspotPrefix4.label"), ("CursorManager", ".walkPrefix.label"),
 ("StoreItem", ".receivedMessage"), ("StoreItem", ".displayName"), ("StoreStock", ".entries[].pitchText"),
 ("StoreStock", ".boughtText"), ("StoreStock", ".greetingText"), ("StoreStock", ".vendorName"), ("StoreStock", ".cantAffordText"),
 ("WarJournal", ".scanPerkTexts[]"), ("WarJournal", ".newBadgeText"), ("WarJournal", ".scanPerkHeading"),
 ("ActionRecoveryPodHeal", ".message"),
 ("AbilityOptionsAsset", ".rows[].label"), ("OptionsMenuAsset", ".rows[].label"), ("InventoryOptionsMenuAsset", ".rows[].label"),
 ("ActionDialogOptionRename", ".newLabel"), ("LocalVariables", ".localVars[].textVal"),
 ("RewiredExamineLabelSync", ".fallbackLabel"),
}
# baked interface texts: also handled line by line when they hold several lines
BAKED = {("TextMeshProUGUI", ".m_text"), ("TextMeshPro", ".m_text"), ("Text", ".m_Text")}
# names: replaced unless the game code mentions the English name literally (it may compare it)
NAMES = {("NPC", ".speechLabel"), ("Player", ".speechLabel"), ("Hotspot", ".hotspotName"), ("ActionCharRename", ".newName")}
ALWAYS = {"Hotspot", "NPC", "Player", "InventoryManager", "WarJournal"}
def patch_fonts(e, de_index=4):
    """Language-font components: English gets the font (and sizes) the German slot used, where the two differ.
    The German slot is the one French was first played on; several English-only pixel fonts lack accented letters."""
    n = 0
    for o in e.objects:
        if o.type.name != "MonoBehaviour": continue
        raw = o.get_raw_data(); key = tt.script_of(o, raw)
        if not key or key[2] not in ("DynamicFontLanguage", "ProfileNameFontLanguage"): continue
        nd = tt.nodes(key)
        try:
            d = tt.decode(raw, nd)
            if tt.encode(d, nd) != raw: continue
        except Exception: continue
        by = {x["languageIndex"]: x for x in d["perLanguageFonts"]}
        if 0 in by and de_index in by:
            a, b = by[0], by[de_index]
            if any(a[k] != b[k] for k in a if k != "languageIndex"):
                for k in a:
                    if k != "languageIndex": a[k] = dict(b[k]) if isinstance(b[k], dict) else b[k]
                o.set_raw_data(tt.encode(d, nd)); n += 1
    return n
class EnSlot:
    def __init__(self, id2en, id2fr, extra, scan):
        self.id2en = id2en; self.id2fr = id2fr
        self.en2fr = {}
        for i, f in id2fr.items():
            e = id2en.get(i)
            if e and f and f != e: self.en2fr.setdefault(e, f)
        self.extra = extra; self.scan = scan; self.extra_used = set()
        self.enb = {e.encode("utf-8") for e in self.en2fr}
        # textes hors table : connus par leur longueur et leur empreinte, pas par leur texte
        self.xlen = {k[2] for k in self.extra}; self.xfp = {(k[2], k[3]) for k in self.extra}
        # names the code mentions only to DISPLAY them (checked by hand in its string table) may be translated
        self.lit = tt.chaines_utf16(tt.D + "Managed/Assembly-CSharp.dll") - {"The Rat", "Speaker", "Buster", "Buster 09"}
        self.applied = collections.Counter(); self.used = set(); self.kept_literal = set(); self.skipped = collections.Counter()
    def quick(self, raw):
        n4 = len(raw) // 4; ints = memoryview(raw)[:n4 * 4].cast("i"); L = len(raw); enb = self.enb
        xlen = self.xlen; xfp = self.xfp; crc = textes.zlib.crc32
        for k in range(7, n4):
            n = ints[k]
            if 0 < n <= 20000:
                a = k * 4 + 4
                if a + n <= L:
                    s = raw[a:a + n]
                    if s in enb: return True
                    if n in xlen and (n, "%08x" % crc(s)) in xfp: return True
                    if b"\n" in s:
                        for p in s.split(b"\n"):
                            if p in enb or p.strip() in enb: return True
        return False
    def multi(self, s):
        out = []; hit = False
        for p in s.split("\n"):
            if p in self.en2fr: out.append(self.en2fr[p]); hit = True; self.used.add(p)
            elif p.strip() in self.en2fr:
                c = p.strip(); a = p.index(c); out.append(p[:a] + self.en2fr[c] + p[a + len(c):]); hit = True; self.used.add(c)
            elif not p.strip(): out.append(p)
            else: return s
        return "\n".join(out) if hit else s
    def repl(self, cls, path, s):
        key = (cls, path)
        if self.extra:
            b = s.encode("utf-8"); n = len(b)
            if n in self.xlen:
                k = (cls, path, n, "%08x" % textes.zlib.crc32(b))
                x = self.extra.get(k)
                if x is not None: self.extra_used.add(k); return x
        if key in FIELDS or key in BAKED:
            f = self.en2fr.get(s)
            if f is not None: self.used.add(s); return f
            if key in BAKED and "\n" in s: return self.multi(s)
        elif key in NAMES:
            f = self.en2fr.get(s)
            if f is not None:
                if s in self.lit: self.kept_literal.add(s); return s
                self.used.add(s); return f
        return s
    def walk(self, v, path, cls):
        n = 0
        if isinstance(v, dict):
            for k, x in v.items():
                if isinstance(x, str):
                    if x:
                        y = self.repl(cls, path + "." + k, x)
                        if y != x: v[k] = y; n += 1; self.applied[cls + path + "." + k] += 1
                elif isinstance(x, list):
                    if x and isinstance(x[0], str):
                        for j, s in enumerate(x):
                            if s:
                                y = self.repl(cls, path + "." + k + "[]", s)
                                if y != s: x[j] = y; n += 1; self.applied[cls + path + "." + k + "[]"] += 1
                    elif x and isinstance(x[0], (dict, list)): n += self.walk(x, path + "." + k, cls)
                elif isinstance(x, dict): n += self.walk(x, path + "." + k, cls)
        elif isinstance(v, list):
            for x in v:
                if isinstance(x, (dict, list)): n += self.walk(x, path + "[]", cls)
        return n
    def special(self, cls, d, o, objs):
        n = 0
        if cls == "InventoryManager":           # item names: the label is an identifier, the in-game name goes in altLabel
            for it in d.get("items", []):
                if not it.get("altLabel") and it.get("label") in self.en2fr and self.id2en.get(it.get("lineID")) == it["label"]:
                    it["altLabel"] = self.en2fr[it["label"]]; self.used.add(it["label"]); n += 1; self.applied["InventoryManager.items[].altLabel(new)"] += 1
        elif cls == "WarJournal":               # built-in enemy descriptions (the name is a lookup key: untouched)
            for c in d.get("creatureDatabase", []):
                f = self.scan.get(c.get("creatureName"))
                if f and c.get("description") and c["description"] != f:
                    c["description"] = f; n += 1; self.applied["WarJournal.creatureDatabase[].description"] += 1
        elif cls in ("Hotspot", "NPC", "Player"):   # empty display name = the game uses the object's name
            k = "hotspotName" if cls == "Hotspot" else "speechLabel"
            if k in d and not d[k] and "lineID" in d:
                en = self.id2en.get(d["lineID"]); go = objs.get(d["m_GameObject"]["m_PathID"])
                if en and en in self.en2fr and go is not None and go.peek_name() == en and en not in self.lit:
                    d[k] = self.en2fr[en]; self.used.add(en); n += 1; self.applied[cls + "." + k + "(empty)"] += 1
        return n
    def patch(self, e, name, skip=()):
        objs = {o.path_id: o for o in e.objects}; changed = 0
        for o in e.objects:
            if o.type.name != "MonoBehaviour" or o.path_id in skip: continue
            raw = o.get_raw_data(); key = tt.script_of(o, raw)
            if key is None: continue
            cls = key[2]
            if cls not in ALWAYS and not self.quick(raw): continue
            nd = tt.nodes(key)
            if nd is None: self.skipped["no typetree:" + cls] += 1; continue
            try:
                d = tt.decode(raw, nd)
                if tt.encode(d, nd) != raw: raise ValueError("roundtrip")
            except Exception:
                self.skipped["unreadable:" + cls] += 1; continue
            n = self.walk(d, "", cls) + self.special(cls, d, o, objs)
            if n: o.set_raw_data(tt.encode(d, nd)); changed += 1
        return changed
