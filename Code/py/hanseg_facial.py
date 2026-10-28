"""Stage 1: facial skeleton (maxilla/palate, zygomatic, nasal, mandible bone, teeth) from CT on the case grid."""
from morph import dil, ero, clo, opn
import SimpleITK as sitk, numpy as np, json, sys
from scipy import ndimage as ndi
case = sys.argv[1] if len(sys.argv) > 1 else "case_02"
root = r"D:/2d_3d_regis dataset/New_version/Data/HaN-Seg/HaN-Seg/HaN-Seg/set_1"
out = f"D:/2d_3d_regis dataset/New_version/outputs/hanseg_{case}"; H = 0.8
ref = sitk.ReadImage(f"{out}/{case}_nested_labels.nii.gz")
lab = sitk.GetArrayFromImage(ref); oar = sitk.GetArrayFromImage(sitk.ReadImage(f"{out}/{case}_oar_labels.nii.gz"))
hu = sitk.GetArrayFromImage(sitk.ReadImage(f"{out}/{case}_CT_HU_head.nii.gz"))
cord = sitk.GetArrayFromImage(sitk.Resample(sitk.ReadImage(f"{root}/{case}/{case}_OAR_SpinalCord.seg.nrrd"), ref, sitk.Transform(), sitk.sitkNearestNeighbor, 0)) > 0
def ball(r_mm):
    r = max(1, int(round(r_mm / H))); g = np.mgrid[-r:r+1, -r:r+1, -r:r+1]; return (g**2).sum(0) <= r*r
head = lab > 0; skull = lab == 2; mand_oar = oar == 7
Z, Y, X = hu.shape
# ---- exclude cervical spine: bone near the cord, below/around skull base
zc_top = np.where(cord.any((1, 2)))[0].max()
dist_cord = np.full(hu.shape, 1e3, np.float32)
zlo = 0; zhi = min(Z, zc_top + 40)
dist_cord[zlo:zhi] = ndi.distance_transform_edt(~cord[zlo:zhi], sampling=H)
bone = (hu >= 250) & head
bone_lo = (hu >= 170) & head
spine = bone & (dist_cord < 32)
spine |= bone & (np.arange(Z)[:, None, None] < zc_top - 10) & (np.arange(Y)[None, :, None] > 0) & (dist_cord < 45)
# ---- mandible bone: bone near HaN-Seg mandible mask
mand = (bone & dil(mand_oar, 3.0) | mand_oar) & ~spine
# ---- teeth: very dense voxels next to jaw
dens = (hu >= 1300) & head
jaw_zone = dil(mand_oar, 6.0)
zm_top = np.where(mand_oar.any((1, 2)))[0].max()
# upper teeth: anterior, dense, in a band around mandible top level and above (to +25 mm)
yant = np.where(head[zm_top - 2])[0].min() if head[zm_top - 2].any() else 0
upper_zone = np.zeros_like(bone); zz = np.arange(Z)[:, None, None]; yy = np.arange(Y)[None, :, None]
upper_zone = (zz >= zm_top - 4) & (zz <= zm_top + int(32 / H)) & (yy <= int(np.where(mand_oar.any((0, 2)))[0].max()) + 5)
teeth = dens & (jaw_zone | upper_zone) & ~skull & ~spine
teeth = opn(teeth, 0.8)
# ---- facial bone = remaining bone not skull/spine/mandible
fb = opn(bone_lo, 1.0) & ~skull & ~spine & ~mand & ~teeth
fb[: max(0, np.where(mand_oar.any((1, 2)))[0].min() - 2)] = False
# keep only parts above the mandible-bottom and within the face: drop everything posterior to the cord front (vertebral/pharynx)
cy = np.where(cord.any((0, 2)))[0]; cord_front = cy.min()
fb[:, cord_front - int(18 / H):, :] = False if False else fb[:, cord_front - int(18 / H):, :] & skull[:, cord_front - int(18/H):, :]
fb = opn(fb, 0.8)
lbl, n = ndi.label(fb); sz = np.bincount(lbl.ravel()); keep = np.where(sz >= 400)[0]; keep = keep[keep > 0]; fb = np.isin(lbl, keep)
fb = clo(fb, 1.6) & head & ~skull & ~spine & ~mand & ~teeth
# ---- split by geometry (scaled to THUMS fractions)
zb = np.where(mand_oar.any((1, 2)))[0].min(); zt = np.where(skull.any((1, 2)))[0].max(); f = (zz - zb) / float(zt - zb)
xs = np.where(skull.any((0, 1)))[0]; xm = 0.5 * (xs.min() + xs.max()); dx = np.abs(np.arange(X)[None, None, :] - xm) * H
zr = (f[:,0,0] >= 0.35) & (f[:,0,0] <= 0.55); nose_y = min(np.where(head[k].any(1))[0].min() for k in np.where(zr)[0] if head[k].any())
nasal = fb & (dx <= 18) & (f >= 0.38) & (f <= 0.62) & (np.arange(Y)[None, :, None] <= nose_y + int(32 / H))
zyg = fb & ~nasal & (dx >= 32) & (f >= 0.28) & (f <= 0.60)
maxi = fb & ~nasal & ~zyg & (f < 0.55)
other = fb & ~nasal & ~zyg & ~maxi
F = np.zeros(hu.shape, np.uint8); F[maxi] = 10; F[zyg] = 11; F[nasal] = 12; F[mand] = 13; F[teeth] = 14; F[other] = 15
im = sitk.GetImageFromArray(F); im.CopyInformation(ref); sitk.WriteImage(im, f"{out}/{case}_facial_labels.nii.gz", True)
names = json.load(open(f"{out}/label_names.json"))
names.update({"10": "Maxilla_palate_alveolar", "11": "Zygomatic", "12": "Nasal_bones", "13": "Mandible_bone_CT", "14": "Teeth", "15": "Facial_other_bone"}); json.dump(names, open(f"{out}/label_names.json", "w"))
vox = H**3 / 1000
for L in range(10, 16): print(names[str(L)], "mL", round((F == L).sum() * vox, 1))
print("skull+facial+mandible+teeth bone vs THUMS-like total (mL):", round(((lab == 2).sum() + (F > 0).sum()) * vox, 1))
# ---- preview
cols = {1: (255,200,150), 2: (255,255,255), 3: (80,160,255), 4: (255,60,60), 10: (255,160,0), 11: (0,220,0), 12: (255,0,255), 13: (0,220,255), 14: (255,255,0), 15: (170,120,60)}
def paint(c, l, f_):
    g = (np.clip((c + 200) / 600, 0, 1) * 130).astype(np.uint8); rgb = np.stack([g]*3, -1).astype(float)
    for k, v in cols.items():
        m = (l == k) if k < 10 else (f_ == k); rgb[m] = 0.2 * rgb[m] + 0.8 * np.array(v)
    return rgb.astype(np.uint8)[::-1]
xc = int(xm); zf = int(zb + 0.25 * (zt - zb)); yf = int(np.where(F == 12)[1].mean()) if (F == 12).any() else 30
p1 = paint(hu[:, :, xc], lab[:, :, xc], F[:, :, xc]); p2 = paint(hu[:, yf, :], lab[:, yf, :], F[:, yf, :]); p3 = paint(hu[zf], lab[zf], F[zf])
def fit(p, h=520):
    im_ = sitk.GetImageFromArray(p, isVector=True); s = h / p.shape[0]
    return sitk.GetArrayFromImage(sitk.Resample(im_, [int(p.shape[1]*s), h], sitk.Transform(), sitk.sitkNearestNeighbor, im_.GetOrigin(), (1/s, 1/s), im_.GetDirection(), 0)).astype(np.uint8)
sitk.WriteImage(sitk.GetImageFromArray(np.concatenate([fit(p1), fit(p2), fit(p3)], 1), isVector=True), f"{out}/{case}_facial_preview.png")
