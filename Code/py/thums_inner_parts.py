import sys, re, numpy as np
sys.path.insert(0, r"D:/2d_3d_regis dataset/New_version/Code/py")
from extract_head import parse_full_k, split_fields
d = parse_full_k(r"D:/2d_3d_regis dataset/New_version/Data/Ls_dyna_model/Head_V6_head_only.k"); xyz = d["node_coords"]
names = {}
for pid, (kw, lines) in d["parts"].items():
    nm = [l.strip() for l in lines if not l.startswith("$") and not l.startswith("*")]; names[pid] = nm[0] if nm else str(pid)
def info(pids):
    ids = set(); ns = nsh = 0; vol = 0.0
    for e, (pid, raw) in d["elems_solid"].items():
        if pid in pids:
            f = split_fields(raw, 10); n = [int(v) for v in f[2:10]]; ids.update(n); ns += 1
            P = np.array([xyz[i] for i in n if i in xyz])
            if len(P) == 8:  # hex volume via tetra split approx
                c = P.mean(0); vol += abs(np.linalg.det(np.array([P[1]-P[0], P[3]-P[0], P[4]-P[0]])))
    for e, (pid, raw) in d["elems_shell"].items():
        if pid in pids:
            f = split_fields(raw, 6); ids.update(int(v) for v in f[2:6] if v and int(v) > 0); nsh += 1
    P = np.array([xyz[i] for i in ids if i in xyz]); return ns, nsh, vol / 1000.0, P
G = {
 "White matter cerebrum": r"White_Matter_Cerebrum", "Gray matter cerebrum": r"Gray_Matter_Cerebrum",
 "White matter cerebellum": r"White_Matter_Cerebellum", "Gray matter cerebellum": r"Gray_Matter_Cerebellum",
 "White matter brainstem": r"White_Matter_Stem", "Gray matter brainstem": r"Gray_Matter_Stem",
 "CSF (all)": r"^CSF", "Ventricles (lateral+3rd)": r"Ventricle", "Pia": r"^Pia", "Arachnoid": r"^Arachnoid", "Medulla surface": r"^Medulla",
 "Tentorium": r"^Tentorium", "Falx": r"^Falx", "Sagittal sinus": r"Sagittal_Sinus", "Dura (shell/internal/hole)": r"^Dura", "Optic nerves": r"optic_nerve",
}
print(f"{'group':28s} parts solids shells  vol~mL   x(AP)  y(LR)  z(SI)   zmin-zmax")
for g, pat in G.items():
    pids = {p for p, n in names.items() if re.search(pat, n)}
    ns, nsh, v, P = info(pids)
    lo, hi = P.min(0), P.max(0)
    print(f"{g:28s} {len(pids):4d} {ns:6d} {nsh:6d} {v:8.1f} {hi[0]-lo[0]:6.1f} {hi[1]-lo[1]:6.1f} {hi[2]-lo[2]:6.1f}  {lo[2]:.0f}-{hi[2]:.0f}")
