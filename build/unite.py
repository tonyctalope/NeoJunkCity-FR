"""Lecture et ecriture des composants du jeu (MonoBehaviour Unity) a partir de leur description de type,
calculee depuis les DLL du jeu lui-meme. Rien n'est ecrit si la relecture ne redonne pas les memes octets."""
import struct, os, re
import UnityPy
from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator

UNITY = "2021.3.20f1"
PRIM = {"UInt8": "B", "SInt8": "b", "bool": "B", "char": "B", "int": "i", "unsigned int": "I", "SInt16": "h", "UInt16": "H",
        "SInt64": "q", "UInt64": "Q", "float": "f", "double": "d", "long long": "q", "unsigned long long": "Q"}
GGM = "globalgamemanagers.assets"
D = None            # dossier "Neo Junk City_Data" (avec separateur final), fixe par config()
_g = None; _nodes = {}; _scripts = None


def config(data_dir):
    global D, _g, _nodes, _scripts
    D = os.path.join(data_dir, ""); _g = None; _nodes = {}; _scripts = None


def gen():
    global _g
    if _g is None:
        _g = TypeTreeGenerator(UNITY); _g.load_local_dll_folder(D + "Managed")
    return _g


def scripts():
    """path_id -> (assembly, namespace, classe) des scripts du jeu"""
    global _scripts
    if _scripts is None:
        _scripts = {}
        for o in UnityPy.load(D + GGM).objects:
            if o.type.name == "MonoScript":
                m = o.read(); _scripts[o.path_id] = (m.m_AssemblyName, m.m_Namespace, m.m_ClassName)
    return _scripts


def script_pid(classe):
    return next(p for p, k in scripts().items() if k[2] == classe)


def script_ref(o, raw=None):
    """path_id du script d'un composant (reference vers globalgamemanagers.assets), ou None"""
    raw = raw if raw is not None else o.get_raw_data()
    if len(raw) < 28:
        return None
    fid, pid = struct.unpack_from("<iq", raw, 16)
    if fid == 0:
        return None
    if os.path.basename(o.assets_file.externals[fid - 1].path).lower() != GGM:
        return None
    return pid


def script_of(o, raw=None):
    """(assembly, namespace, classe) d'un composant, ou None"""
    pid = script_ref(o, raw)
    return None if pid is None else scripts().get(pid)


def nodes(key):
    if key not in _nodes:
        asm, ns, cn = key
        full = (ns + "." if ns else "") + cn
        try:
            _nodes[key] = gen().get_nodes_up(asm[:-4] if asm.endswith(".dll") else asm, full)
        except Exception:
            _nodes[key] = None
    return _nodes[key]


def _isstr(n):
    ch = n.m_Children
    return n.m_Type == "string" and (not ch or ch[0].m_Children[1].m_Type == "char")


def decode(raw, root, octets=True):
    """octets=True : les tableaux d'octets restent des bytes (rapide) ; False : listes d'entiers (table des dialogues)."""
    pos = 0

    def rd(n):
        nonlocal pos
        t = n.m_Type; ch = n.m_Children
        if t in PRIM:
            f = PRIM[t]; v = struct.unpack_from("<" + f, raw, pos)[0]; pos += struct.calcsize(f)
        elif _isstr(n):
            ln = struct.unpack_from("<i", raw, pos)[0]; pos += 4
            if ln < 0 or pos + ln > len(raw):
                raise ValueError("bad string length")
            v = raw[pos:pos + ln].decode("utf-8"); pos += ln; pos = (pos + 3) & ~3; return v
        elif ch and ch[0].m_Type == "Array":
            ln = struct.unpack_from("<i", raw, pos)[0]; pos += 4
            if ln < 0 or ln > len(raw):
                raise ValueError("bad array length")
            el = ch[0].m_Children[1]
            if octets and el.m_Type in ("UInt8", "char", "SInt8"):
                v = bytes(raw[pos:pos + ln]); pos += ln
            else:
                v = [rd(el) for _ in range(ln)]
            pos = (pos + 3) & ~3; return v
        elif not ch:
            raise ValueError("unknown leaf type " + t)
        else:
            v = {c.m_Name: rd(c) for c in ch}
        if n.m_MetaFlag & 0x4000:
            pos = (pos + 3) & ~3
        return v
    v = rd(root)
    if pos != len(raw):
        raise ValueError("size mismatch %d/%d" % (pos, len(raw)))
    return v


def encode(obj, root):
    out = bytearray()

    def align():
        while len(out) % 4:
            out.append(0)

    def wr(n, v):
        t = n.m_Type; ch = n.m_Children
        if t in PRIM:
            out.extend(struct.pack("<" + PRIM[t], v))
        elif _isstr(n):
            b = v.encode("utf-8"); out.extend(struct.pack("<i", len(b))); out.extend(b); align(); return
        elif ch and ch[0].m_Type == "Array":
            out.extend(struct.pack("<i", len(v))); el = ch[0].m_Children[1]
            if isinstance(v, bytes):
                out.extend(v)
            else:
                for x in v:
                    wr(el, x)
            align(); return
        else:
            for c in ch:
                wr(c, v[c.m_Name])
        if n.m_MetaFlag & 0x4000:
            align()
    wr(root, obj)
    return bytes(out)


def chaines_utf16(chemin):
    """Chaines lisibles (UTF-16, comme les litteraux du code .NET) d'un fichier : equivalent de `strings -e l -n 2`."""
    data = open(chemin, "rb").read()
    return {m.group().decode("utf-16-le") for m in re.finditer(rb"(?:[\x20-\x7e\t]\x00){2,}", data)}
