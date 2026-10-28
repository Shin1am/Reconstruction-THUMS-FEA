"""Stage 2: ventricles (MR-based) and approximate cerebellum/cerebrum split (geometry-based tentorium plane)."""
from morph import dil, ero, clo, opn
import SimpleITK as sitk, numpy as np, json, sys
from scipy import ndimage as ndi
case = sys.argv[1] if len(sys.argv) > 1 else "case_02"
out = f"D:/2d_3d_regis dataset/New_version/outputs/hanseg_{case}"; H = 0.8
ref = sitk.ReadImage(f"{out}/{case}_nested_labels.nii.gz")
lab = sitk.GetArrayFromImage(ref); oar = sitk.GetArrayFromImage(sitk.ReadImage(f"{out}/{case}_oar_labels.nii.gz"))
mr = sitk.GetArrayFromImage(sitk.SmoothingRecursiveGaussian(sitk.ReadImage(f"{out}/{case}_MR_head.nii.gz"), 0.8))
Z, Y, X = lab.shape
def ball(r):
    r = max(1, int(round(r / H))); g = np.mgrid[-r:r+1, -r:r+1, -r:r+1]; return (g**2).sum(0) <= r*r
brain = lab == 4; bs = oar == 5
covered = mr > 0.02 * mr.max()
inner = ero(brain, 3.0) & covered
# per-slice shading correction (MR signal falls off toward the vertex)
med = np.zeros(Z)
for k in range(Z):
    m_ = inner[k]
    med[k] = np.median(mr[k][m_]) if m_.sum() > 200 else np.nan
ok = ~np.isnan(med); med = np.interp(np.arange(Z), np.where(ok)[0], med[ok]); med = ndi.gaussian_filter1d(med, 6)
mr = mr / med[:, None, None] * np.median(med)
# --- 3-class k-means on MR intensity inside brain (CSF / GM / WM)
v = mr[inner]; c = np.percentile(v, [10, 50, 90]).astype(float)
for _ in range(30):
    a = np.argmin(np.abs(v[:, None] - c[None]), 1); c = np.array([v[a == k].mean() for k in range(3)])
print("kmeans centers (CSF/GM/WM):", c)
thr = 0.5 * (c[0] + c[1])
bz0 = np.where((oar == 5).any((1, 2)))[0].max()
zz0, yy0, xx0 = np.indices(brain.shape)
zs_, ys_, xs_ = np.where(brain); cy0, cx0 = ys_.mean(), xs_.mean()
roi = (zz0 >= bz0 + 3 / H) & (zz0 <= bz0 + 62 / H) & (np.abs(xx0 - cx0) * H < 38) & (np.abs(yy0 - cy0) * H < 62)
deep = ero(brain, 8.0) & covered
csf = deep & roi & (mr < thr)
# keep central cavities: components in the central brain region with decent size
lbl, n = ndi.label(opn(csf, 1.0))
zs, ys, xs = np.where(brain); cz, cy, cx = zs.mean(), ys.mean(), xs.mean()
vent = np.zeros_like(brain)
for i in range(1, n + 1):
    m = lbl == i; vol = m.sum() * H**3 / 1000
    if vol < 0.4: continue
    zz, yy, xx = np.where(m); d = np.sqrt(((zz.mean() - cz) * H)**2 + ((yy.mean() - cy) * H)**2 + ((xx.mean() - cx) * H)**2)
    if d < 45: vent |= m
vent = dil(vent, 1.0) & brain & covered
print("ventricles mL", vent.sum() * H**3 / 1000)
# --- brainstem + tentorium plane
bz = np.where(bs.any((1, 2)))[0]; btop = bz.max()
top_sl = bs[btop - 6:btop + 1]; _, by, bx = np.where(top_sl)
Ay, Ax, Az = by.mean(), bx.mean(), btop            # brainstem top centroid (midline reference)
inner_skull = (lab == 3) | brain
zr = np.arange(int(Az - 40 / H), int(Az + 5 / H))
post = max(np.where(inner_skull[k].any(1))[0].max() for k in zr if inner_skull[k].any())  # most posterior cavity (AP index)
By = post; Bz = Az - 22 / H
slope = (Az - Bz) / max(1.0, (By - Ay))                       # z rises toward anterior
yy_, xx_ = np.mgrid[0:Y, 0:X]
zplane = Az - slope * (yy_ - Ay)                                # at y=Ay z=Az, falls posteriorly (higher y)
zplane = zplane - 0.35 * np.abs(xx_ - Ax) * 1.0                 # tent: droops laterally
zgrid = np.arange(Z)[:, None, None]
np.save(f"{out}/tent_zplane.npy", zplane); json.dump({"Ay": float(Ay), "Ax": float(Ax), "Az": float(Az)}, open(f"{out}/tent_params.json", "w"))
below = zgrid < zplane[None]
post_of_bs = (np.arange(Y)[None, :, None] > (np.where(bs.any((0, 2)))[0].min() + 4))
cb = brain & below & post_of_bs & ~bs & ~vent
cb = cb & (np.arange(Y)[None, :, None] > Ay - 6 / H)
l2, n2 = ndi.label(cb); cb = l2 == (np.argmax(np.bincount(l2.ravel())[1:]) + 1)
cer = brain & ~bs & ~vent & ~cb
cer_cb = cb
print("cerebellum(approx) mL", cb.sum() * H**3 / 1000, "cerebrum(approx) mL", cer.sum() * H**3 / 1000)
zz, yy, xx = np.where(cb); print("cerebellum size mm  AP", (yy.max() - yy.min()) * H, " LR", (xx.max() - xx.min()) * H, " SI", (zz.max() - zz.min()) * H, " (THUMS ~61 / 106 / 55)")
S = np.zeros(lab.shape, np.uint8); S[cer] = 22; S[cb] = 21; S[vent] = 20
im = sitk.GetImageFromArray(S); im.CopyInformation(ref); sitk.WriteImage(im, f"{out}/{case}_stage2_labels.nii.gz", True)
json.dump({"20": {"name": "Ventricles_MR", "color": [0.2, 0.9, 0.9]}, "21": {"name": "Cerebellum_approx", "color": [0.4, 0.4, 1.0]}, "22": {"name": "Cerebrum_approx", "color": [1.0, 0.5, 0.5]}}, open(f"{out}/stage2_names.json", "w"))
# --- preview (MR + labels)
cols = {20: (0, 255, 255), 21: (80, 80, 255), 22: (255, 120, 120)}
mrv = sitk.GetArrayFromImage(sitk.ReadImage(f"{out}/{case}_MR_head.nii.gz")); mv = np.percentile(mrv[brain & covered], 99.5)
def paint(m_, s_):
    g = (np.clip(m_ / mv, 0, 1) * 255).astype(np.uint8); rgb = np.stack([g]*3, -1).astype(float)
    for k, vv in cols.items(): mm = s_ == k; rgb[mm] = 0.55 * rgb[mm] + 0.45 * np.array(vv)
    return rgb.astype(np.uint8)[::-1]
xc, yc, zc = int(Ax), int(cy), int((cz + btop) / 2)
def fit(p, h=520):
    im_ = sitk.GetImageFromArray(p, isVector=True); s = h / p.shape[0]
    return sitk.GetArrayFromImage(sitk.Resample(im_, [int(p.shape[1]*s), h], sitk.Transform(), sitk.sitkNearestNeighbor, im_.GetOrigin(), (1/s, 1/s), im_.GetDirection(), 0)).astype(np.uint8)
ax = paint(mrv[int(cz + 12 / H)], S[int(cz + 12 / H)])
sitk.WriteImage(sitk.GetImageFromArray(np.concatenate([fit(paint(mrv[:, :, xc], S[:, :, xc])), fit(paint(mrv[:, yc, :], S[:, yc, :])), fit(ax)], 1), isVector=True), f"{out}/{case}_stage2_preview.png")
