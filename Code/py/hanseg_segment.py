"""Build nested head labels (CT-based) + OAR extras for a HaN-Seg case on a 0.8mm iso cropped grid.
usage: hanseg_segment.py case_XX  (needs outputs/hanseg_<case>/<case>_MR_in_CT.nii.gz)"""
from morph import dil, ero, clo, opn
import SimpleITK as sitk, numpy as np, sys, os
from scipy import ndimage as ndi
root = r"D:/2d_3d_regis dataset/New_version/Data/HaN-Seg/HaN-Seg/HaN-Seg/set_1"
case = sys.argv[1]; out = f"D:/2d_3d_regis dataset/New_version/outputs/hanseg_{case}"
H = 0.8
ct = sitk.ReadImage(f"{root}/{case}/{case}_IMG_CT.nrrd", sitk.sitkFloat32)
mr = sitk.ReadImage(f"{out}/{case}_MR_in_CT.nii.gz")

def ball(r_mm):
    r = max(1, int(round(r_mm / H))); g = np.mgrid[-r:r+1, -r:r+1, -r:r+1]
    return (g**2).sum(0) <= r*r
def largest(m):
    l, n = ndi.label(m)
    return l == (np.argmax(np.bincount(l.ravel())[1:]) + 1) if n else m

# --- head extent on coarse grid
cd = sitk.Shrink(ct, [3, 3, 1]); a = sitk.GetArrayFromImage(cd) > -300
a = ndi.binary_opening(a, iterations=3); a = largest(a)
zs = np.where(a.any((1, 2)))[0]; sp = cd.GetSpacing(); o = cd.GetOrigin()
ztop = o[2] + zs.max() * sp[2]; zbot = ztop - 250
ys, xs = np.where(a[zs.min():zs.max()+1].any(0))
bx = (o[0] + xs.min()*sp[0] - 10, o[0] + xs.max()*sp[0] + 10); by = (o[1] + ys.min()*sp[1] - 10, o[1] + ys.max()*sp[1] + 10)
print("ztop", ztop, "zbot", zbot, "x", bx, "y", by)
# --- target grid
size = [int((bx[1]-bx[0])/H), int((by[1]-by[0])/H), int((ztop+5-zbot)/H)]
ref = sitk.Image(size, sitk.sitkFloat32); ref.SetSpacing((H, H, H)); ref.SetOrigin((bx[0], by[0], zbot))
ref.SetDirection((1,0,0,0,1,0,0,0,1)); print("grid", size)
ctr = sitk.Resample(ct, ref, sitk.Transform(), sitk.sitkLinear, -1000.0)
mrr = sitk.Resample(mr, ref, sitk.Transform(), sitk.sitkLinear, 0.0)
hu = sitk.GetArrayFromImage(ctr)

# --- head (skin) mask
head = opn(hu > -300, 2.0); head = largest(head)
head = clo(head, 1.6)
for k in range(head.shape[0]): head[k] = ndi.binary_fill_holes(head[k])
# --- bone, cavity, brain
zc = int((ztop - 165 - zbot) / H)                     # only cranial levels
bone = (hu >= 250) & head; bone[:zc] = False
bone = opn(bone, 0.8)
closed = clo(bone, 4.0)
filled = np.zeros_like(closed)
for k in range(closed.shape[0]): filled[k] = ndi.binary_fill_holes(closed[k])
intra = filled & ~dil(bone, 0.8)
soft = (hu > -5) & (hu < 90)
brain = largest(ero(intra & soft, 1.6))
brain = dil(brain, 1.6) & intra & soft
# --- caudal extension: 2D fill fails where the ring opens (orbit/skull base).
# Propagate slice by slice downward: convex hull of cranial bone near the slice above.
from scipy.spatial import Delaunay
rr = int(round(10 / H)); yy, xx = np.mgrid[-rr:rr+1, -rr:rr+1]; disk = (yy**2 + xx**2) <= rr*rr
ks = int(np.where(brain.any((1, 2)))[0].min())
for k in range(ks - 1, zc - 1, -1):
    prev = ndi.binary_dilation(brain[k + 1], structure=disk)
    cand = bone[k] & prev
    if cand.sum() < 50: break
    pts = np.argwhere(cand)
    try: tri = Delaunay(pts)
    except Exception: break
    y0, x0 = pts.min(0); y1, x1 = pts.max(0)
    gy, gx = np.mgrid[y0:y1+1, x0:x1+1]
    inside = tri.find_simplex(np.c_[gy.ravel(), gx.ravel()]) >= 0
    hull = np.zeros(bone[k].shape, bool); hull[y0:y1+1, x0:x1+1] = inside.reshape(gy.shape)
    filled[k] = hull
    ik = hull & ~ndi.binary_dilation(bone[k], structure=disk[rr-1:rr+2, rr-1:rr+2])
    intra[k] = ik
    bk = ndi.binary_opening(ik & soft[k], structure=disk[rr-2:rr+3, rr-2:rr+3])
    l2, n2 = ndi.label(bk)
    if n2 == 0: break
    bk = l2 == (np.argmax(np.bincount(l2.ravel())[1:]) + 1)
    brain[k] = ndi.binary_fill_holes(bk)
brain = clo(brain, 2.4) & intra
brain = largest(brain)
for k in range(brain.shape[0]): brain[k] = ndi.binary_fill_holes(brain[k])
shell = dil(brain, 3.0) & filled & ~brain
cav = brain | shell
skull = bone & dil(cav, 12.0)
skull = clo(skull, 3.0) & ~cav
skull = largest(skull)
skull &= head

lab = np.zeros(hu.shape, np.uint8)
lab[head] = 1; lab[skull] = 2; lab[shell & ~skull] = 3; lab[brain] = 4
# nesting check
assert not (brain & skull).any()

# --- extra OAR labels from HaN-Seg
extras = {5: ["Brainstem"], 6: ["Eye_AL", "Eye_AR", "Eye_PL", "Eye_PR"], 7: ["Bone_Mandible"], 8: ["OpticNrv_L", "OpticNrv_R", "OpticChiasm"], 9: ["Cochlea_L", "Cochlea_R"]}
names = {1: "Scalp_skin", 2: "Skull", 3: "CSF_meninges_shell", 4: "Brain", 5: "Brainstem(OAR)", 6: "Eyes(OAR)", 7: "Mandible(OAR)", 8: "OpticNerves_Chiasm(OAR)", 9: "Cochleae(OAR)"}
ex = np.zeros(hu.shape, np.uint8)
for L, ns in extras.items():
    for n in ns:
        p = f"{root}/{case}/{case}_OAR_{n}.seg.nrrd"
        if not os.path.exists(p): print("missing", n); continue
        m = sitk.Resample(sitk.ReadImage(p), ref, sitk.Transform(), sitk.sitkNearestNeighbor, 0)
        ex[sitk.GetArrayFromImage(m) > 0] = L
ex_only = ex > 0

def save(arr, name, dtype):
    im = sitk.GetImageFromArray(arr.astype(dtype)); im.CopyInformation(ref); sitk.WriteImage(im, f"{out}/{name}", True)
save(lab, f"{case}_nested_labels.nii.gz", np.uint8)
save(ex, f"{case}_oar_labels.nii.gz", np.uint8)
sitk.WriteImage(ctr, f"{out}/{case}_CT_HU_head.nii.gz", True)
sitk.WriteImage(mrr, f"{out}/{case}_MR_head.nii.gz", True)
import json; json.dump(names, open(f"{out}/label_names.json", "w"))
vox = H**3 / 1000
for L in (1,2,3,4): print(names[L], "mL", round((lab == L).sum() * vox, 1))
# skull thickness along rays: use distance transforms
dt_out = ndi.distance_transform_edt(~cav, sampling=H)   # distance from cavity
sk = skull
thick = 2 * dt_out[sk & (ndi.binary_erosion(sk) == 0)] if False else None
print("skull median thickness proxy (mm):", float(np.median(ndi.distance_transform_edt(skull, sampling=H)[skull]) * 2))
