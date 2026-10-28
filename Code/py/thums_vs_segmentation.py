"""Compare THUMS head skull-part extents with the HaN-Seg case segmentation."""
import sys, re, numpy as np, SimpleITK as sitk
sys.path.insert(0, r"D:/2d_3d_regis dataset/New_version/Code/py")
from extract_head import parse_full_k, split_fields
K = r"D:/2d_3d_regis dataset/New_version/Data/Ls_dyna_model/Head_V6_head_only.k"
d = parse_full_k(K); xyz = d["node_coords"]
names = {}
for pid, (kw, lines) in d["parts"].items():
    nm = [l.strip() for l in lines if not l.startswith("$") and not l.startswith("*")]
    names[pid] = nm[0] if nm else str(pid)
if not any(names.values()): print("no names")
def pts_of(pids):
    ids = set()
    for store, nn in ((d["elems_solid"], 8), (d["elems_shell"], 4)):
        for e, (pid, raw) in store.items():
            if pid in pids:
                f = split_fields(raw, 2 + nn); ids.update(int(v) for v in f[2:2+nn] if v and int(v) > 0)
    return np.array([xyz[i] for i in ids if i in xyz])
groups = {
 "cranium (frontal/parietal/temporal/occipital)": [p for p, n in names.items() if re.match(r"(frontal|parietal|temporal|occipital)_[rl]$|temporal_shell", n)],
 "sphenoid+ethmoid": [p for p, n in names.items() if re.match(r"(sphenoid|ethmoid)", n) and "external" not in n and "internal" not in n],
 "nasal/lacrimal/vomer": [p for p, n in names.items() if re.match(r"(nasal|lacrimal|vomer)", n) and "external" not in n and "internal" not in n],
 "zygomatic": [p for p, n in names.items() if n.startswith("zygomatic") and "external" not in n and "internal" not in n],
 "maxilla+palatine+alveolar": [p for p, n in names.items() if re.match(r"(maxilla|palatine|alveolar)", n) and "external" not in n and "internal" not in n],
 "mandible": [p for p, n in names.items() if n.startswith("mandible") and "external" not in n and "internal" not in n],
 "teeth": [p for p, n in names.items() if n.startswith("teeth")],
 "skin (all)": [p for p, n in names.items() if "skin" in n],
 "brain parenchyma": [p for p, n in names.items() if re.match(r"(White|Gray)_Matter", n)],
}
allsk = [p for p in names if 88000001 <= p < 88000100]
print("THUMS node count", len(xyz)); res = {}
for g, pids in list(groups.items()) + [("ALL skull parts 88000001-99", allsk)]:
    P = pts_of(set(pids))
    if len(P) == 0: print(g, "NO NODES", [names[p] for p in pids][:5]); continue
    res[g] = P; lo, hi = P.min(0), P.max(0)
    print(f"{g:50s} parts={len(pids):3d} nodes={len(P):6d} size(mm) x={hi[0]-lo[0]:6.1f} y={hi[1]-lo[1]:6.1f} z={hi[2]-lo[2]:6.1f} | zmin={lo[2]:7.1f} zmax={hi[2]:7.1f}")
np.save(r"D:/2d_3d_regis dataset/New_version/outputs/thums_groups_ranges.npy", {g: (p.min(0), p.max(0)) for g, p in res.items()}, allow_pickle=True)
# our segmentation
out = r"D:/2d_3d_regis dataset/New_version/outputs/hanseg_case_02"
lab = sitk.ReadImage(f"{out}/case_02_nested_labels.nii.gz"); oar = sitk.ReadImage(f"{out}/case_02_oar_labels.nii.gz")
sp = np.array(lab.GetSpacing())
def ext(img, L):
    a = sitk.GetArrayFromImage(img) == L; idx = np.argwhere(a)
    if not len(idx): return None
    lo, hi = idx.min(0)[::-1], idx.max(0)[::-1]; return (hi - lo + 1) * sp, lo, hi
for nm, img, L in (("OUR skull label", lab, 2), ("OUR brain", lab, 4), ("OUR skin", lab, 1), ("OUR mandible (HaN-Seg OAR)", oar, 7)):
    e = ext(img, L); print(f"{nm:50s} size(mm) x={e[0][0]:6.1f} y={e[0][1]:6.1f} z={e[0][2]:6.1f}")
# vertex-relative z-extent of our skull and bone-in-head below
ct = sitk.GetArrayFromImage(sitk.ReadImage(f"{out}/case_02_CT_HU_head.nii.gz")); L = sitk.GetArrayFromImage(lab)
bone = ct >= 250; head = L > 0
print("bone volume in head mL:", round((bone & head).sum() * sp.prod() / 1000, 1), " in our skull label mL:", round(((L == 2)).sum() * sp.prod() / 1000, 1))
zprof = (bone & head).sum((1, 2)) * sp[0] * sp[1] / 100  # cm2 per axial slice
z_sk = np.where((L == 2).any((1, 2)))[0]; print("skull label z-slices", z_sk.min(), z_sk.max(), "of", L.shape[0], "(index 0 = lowest)")
