#!/usr/bin/env python3
"""Fabrique le dossier patch/ (fichiers de différences VFP1 + manifest.json) à partir de deux dossiers :
les fichiers d'origine du jeu et les fichiers traduits. Le patch ne contient que ce qui diffère.
Usage : vfdelta.py <dossier origine> <dossier traduit> <dossier patch> --build N --version X [chemins relatifs...]"""
import sys, os, json, zlib, struct, hashlib, argparse
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import vf

COARSE = 64      # premier passage : blocs de 64 octets pris tous les 64 octets dans l'original
FINE = 12        # second passage, dans les zones restantes : correspondances d'au moins 12 octets


def common(a, i, b, j):
    """longueur du préfixe commun de a[i:] et b[j:]"""
    n = min(len(a) - i, len(b) - j); k = 0; step = 1 << 16
    while k < n:
        s = min(step, n - k)
        if a[i + k:i + k + s] == b[j + k:j + k + s]:
            k += s; continue
        if s == 1:
            break
        lo, hi = 0, s                      # a[..lo] égal, différence avant hi
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if a[i + k:i + k + mid] == b[j + k:j + k + mid]: lo = mid
            else: hi = mid
        return k + lo
    return k


def matches(a, a_lo, a_hi, b, b_lo, b_hi, size, stride):
    """correspondances gloutonnes (b_pos, a_pos, longueur) de b[b_lo:b_hi] dans a[a_lo:a_hi], dans l'ordre de b"""
    idx = {}
    for o in range(a_lo, a_hi - size + 1, stride):
        idx.setdefault(a[o:o + size] if size <= 16 else hash(a[o:o + size]), o)
    out = []; p = b_lo; floor = b_lo
    while p + size <= b_hi:
        blk = b[p:p + size]
        o = idx.get(blk if size <= 16 else hash(blk))
        if o is None or a[o:o + size] != blk:
            p += 1; continue
        back = 0
        while p - back > floor and o - back > a_lo and a[o - back - 1] == b[p - back - 1]:
            back += 1
        ln = size + common(a[:a_hi] if a_hi < len(a) else a, o + size, b[:b_hi] if b_hi < len(b) else b, p + size)
        out.append((p - back, o - back, ln + back))
        p += ln; floor = p
    return out


def delta(a, b):
    """liste d'opérations ('c', position, longueur) / ('i', octets) qui reconstruit b à partir de a"""
    ops = []

    def ins(lo, hi):
        if hi > lo:
            if ops and ops[-1][0] == "i": ops[-1] = ("i", ops[-1][1] + b[lo:hi])
            else: ops.append(("i", b[lo:hi]))

    def cpy(o, ln):
        if ops and ops[-1][0] == "c" and ops[-1][1] + ops[-1][2] == o: ops[-1] = ("c", ops[-1][1], ops[-1][2] + ln)
        else: ops.append(("c", o, ln))

    def gap(a_lo, a_hi, b_lo, b_hi):
        """zone de b sans correspondance : on cherche plus finement dans la zone voisine de a"""
        if b_hi - b_lo < FINE or a_hi - a_lo < FINE:
            ins(b_lo, b_hi); return
        A = a[a_lo:a_hi]; B = b[b_lo:b_hi]; p = 0
        for bp, ap, ln in matches(A, 0, len(A), B, 0, len(B), FINE, 1):
            ins(b_lo + p, b_lo + bp); cpy(a_lo + ap, ln); p = bp + ln
        ins(b_lo + p, b_hi)

    co = matches(a, 0, len(a), b, 0, len(b), COARSE, COARSE)
    bp_prev = 0; ap_prev = 0
    for bp, ap, ln in co:
        gap(ap_prev, ap, bp_prev, bp) if ap >= ap_prev else ins(bp_prev, bp)
        cpy(ap, ln); bp_prev = bp + ln; ap_prev = max(ap_prev, ap + ln)
    gap(ap_prev, len(a), bp_prev, len(b))
    return ops


def encode(ops):
    out = bytearray(struct.pack("<i", len(ops)))
    for op in ops:
        if op[0] == "c": out += struct.pack("<bqi", 0, op[1], op[2])
        else: out += struct.pack("<bi", 1, len(op[1])) + op[1]
    z = zlib.compressobj(9, zlib.DEFLATED, -15)
    return b"VFP1" + z.compress(bytes(out)) + z.flush()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def make(orig_dir, new_dir, patch_dir, build, version, rels=None):
    os.makedirs(patch_dir, exist_ok=True)
    if not rels:
        rels = sorted(os.path.relpath(os.path.join(r, f), new_dir).replace(os.sep, "/")
                      for r, _, fs in os.walk(new_dir, followlinks=True) for f in fs)
    files = []; tot = 0; lit = 0
    for rel in rels:
        a = open(os.path.join(orig_dir, rel), "rb").read(); b = open(os.path.join(new_dir, rel), "rb").read()
        if a == b:
            continue
        ops = delta(a, b); blob = encode(ops)
        name = rel.replace("/", "__") + ".vfp"
        p = os.path.join(patch_dir, name); open(p, "wb").write(blob)
        tmp = p + ".check"; vf.apply_patch(os.path.join(orig_dir, rel), p, tmp)     # contrôle : le patch redonne bien b
        ok = open(tmp, "rb").read() == b; os.remove(tmp)
        assert ok, rel
        files.append({"path": rel, "patch": name, "orig_sha256": sha(a), "orig_size": len(a), "new_sha256": sha(b), "new_size": len(b)})
        tot += len(blob); lit += sum(len(o[1]) for o in ops if o[0] == "i")
        print(f"  {rel}: {len(ops)} opérations, {len(blob)} octets")
    json.dump({"format": 1, "game": "Neo Junk City", "build": str(build), "patch_version": str(version), "files": files},
              open(os.path.join(patch_dir, "manifest.json"), "w", encoding="utf-8"), indent=1)
    print(f"{len(files)} fichiers, patch de {tot} octets ({lit} octets de données nouvelles avant compression)")
    return files


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("orig"); ap.add_argument("new"); ap.add_argument("patch")
    ap.add_argument("--build", required=True); ap.add_argument("--version", default="1.0"); ap.add_argument("rels", nargs="*")
    x = ap.parse_args()
    make(x.orig, x.new, x.patch, x.build, x.version, x.rels)
