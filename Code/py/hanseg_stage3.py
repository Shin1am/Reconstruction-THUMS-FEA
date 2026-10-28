"""Stage 3: APPROXIMATE dura / falx / tentorium shells (geometry, not imaging)."""
from morph import dil, ero, clo, opn
import SimpleITK as sitk, numpy as np, json, sys
from scipy import ndimage as ndi
case = sys.argv[1] if len(sys.argv) > 1 else "case_02"
out = f"D:/2d_3d_regis dataset/New_version/outputs/hanseg_{case}"; H = 0.8
ref = sitk.ReadImage(f"{out}/{case}_nested_labels.nii.gz")
lab = sitk.GetArrayFromImage(ref); oar = sitk.GetArrayFromImage(sitk.ReadImage(f"{out}/{case}_oar_labels.nii.gz"))
s2 = sitk.GetArrayFromImage(sitk.ReadImage(f"{out}/{case}_stage2_labels.nii.gz")); zplane = np.load(f"{out}/tent_zplane.npy"); P = json.load(open(f"{out}/tent_params.json"))
Z, Y, X = lab.shape
def ball(r):
    r = max(1, int(round(r / H))); g = np.mgrid[-r:r+1, -r:r+1, -r:r+1]; return (g**2).sum(0) <= r*r
cav = (lab == 3) | (lab == 4); brain = lab == 4
# dura: outermost ~1.6 mm layer of the intracranial cavity, against the inner table
dura = cav & ~ero(cav, 1.6)
# falx: midsagittal sheet
zs, ys, xs = np.where(brain); xm = xs.mean()
sheet = np.zeros_like(cav); xi = int(round(xm)); half = max(1, int(round(0.8 / H))); sheet[:, :, xi - half:xi + half + 1] = True
vent = s2 == 20
_l, _n = ndi.label(vent); vmain = _l == (np.argmax(np.bincount(_l.ravel())[1:]) + 1) if _n else vent
vz, vy, vx = np.where(vmain)
vtop = vz.max() if len(vz) else int(zs.mean()); ysp = vy.max() if len(vy) else int(ys.mean())
zgrid = np.arange(Z)[:, None, None]; ygrid = np.arange(Y)[None, :, None]
zlow = np.where(ygrid <= ysp, vtop + 6 / H, zplane[:, xi][None, :, None] if False else zplane[:, xi][None, :, None])
falx = sheet & cav & (zgrid >= zlow) & ~vent
# tentorium: thin surface along the same plane used for the cerebellum split, with a notch around the brainstem
tent_band = np.abs(zgrid - zplane[None]) * H <= 0.8
bs = oar == 5; bz = np.where(bs.any((1, 2)))[0].max()
notch = ndi.binary_dilation(bs[bz - 8:bz + 6].any(0), structure=np.ones((int(14 / H) * 2 + 1,) * 2, bool))
tent = cav & tent_band & ~notch[None] & (ygrid > P["Ay"] - 6 / H) & ~(s2 == 21) & ~(s2 == 20) | (cav & tent_band & ~notch[None] & (ygrid > P["Ay"] - 6 / H))
tent &= ~(brain & (zgrid < zplane[None] - 0.0) & False)
S = np.zeros(lab.shape, np.uint8); S[dura] = 30; S[falx] = 31; S[tent] = 32
im = sitk.GetImageFromArray(S); im.CopyInformation(ref); sitk.WriteImage(im, f"{out}/{case}_stage3_labels.nii.gz", True)
json.dump({"30": {"name": "Dura_approx", "color": [0.9, 0.8, 0.2]}, "31": {"name": "Falx_approx", "color": [0.2, 0.6, 0.2]}, "32": {"name": "Tentorium_approx", "color": [0.8, 0.4, 0.1]}}, open(f"{out}/stage3_names.json", "w"))
v = H**3 / 1000
for L, n in ((30, "dura"), (31, "falx"), (32, "tentorium")):
    zz, yy, xx = np.where(S == L); print(n, "mL", round((S == L).sum() * v, 2), " AP/LR/SI mm", round((yy.max()-yy.min())*H), round((xx.max()-xx.min())*H), round((zz.max()-zz.min())*H))
print("THUMS ref: falx AP161 SI97 | tentorium AP102 LR120 SI32")
# preview
mr = sitk.GetArrayFromImage(sitk.ReadImage(f"{out}/{case}_MR_head.nii.gz")); mv = np.percentile(mr[brain & (mr > 0)], 99.5)
cols = {30: (255, 220, 0), 31: (0, 255, 0), 32: (255, 120, 0)}
def paint(m_, s_):
    g = (np.clip(m_ / mv, 0, 1) * 255).astype(np.uint8); rgb = np.stack([g]*3, -1).astype(float)
    for k, c in cols.items(): rgb[s_ == k] = c
    return rgb.astype(np.uint8)[::-1]
def fit(p, h=520):
    im_ = sitk.GetImageFromArray(p, isVector=True); s = h / p.shape[0]
    return sitk.GetArrayFromImage(sitk.Resample(im_, [int(p.shape[1]*s), h], sitk.Transform(), sitk.sitkNearestNeighbor, im_.GetOrigin(), (1/s, 1/s), im_.GetDirection(), 0)).astype(np.uint8)
yc = int(ys.mean()); xc = xi + 12
sitk.WriteImage(sitk.GetImageFromArray(np.concatenate([fit(paint(mr[:, :, xc - 12 + 6], S[:, :, xc - 12 + 6])), fit(paint(mr[:, yc, :], S[:, yc, :])), fit(paint(mr[:, int(P["Ay"]) + 25, :], S[:, int(P["Ay"]) + 25, :]))], 1), isVector=True), f"{out}/{case}_stage3_preview.png")
