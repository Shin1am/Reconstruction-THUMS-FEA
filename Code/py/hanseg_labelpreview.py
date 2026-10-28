import SimpleITK as sitk, numpy as np, sys
case = sys.argv[1]; out = f"D:/2d_3d_regis dataset/New_version/outputs/hanseg_{case}"
ct = sitk.GetArrayFromImage(sitk.ReadImage(f"{out}/{case}_CT_HU_head.nii.gz"))
lab = sitk.GetArrayFromImage(sitk.ReadImage(f"{out}/{case}_nested_labels.nii.gz"))
cols = {1: (255,200,150), 2: (255,255,255), 3: (80,160,255), 4: (255,60,60)}
def panel(c, l):
    g = (np.clip((c + 200) / 600, 0, 1) * 255).astype(np.uint8); rgb = np.stack([g]*3, -1).astype(float)
    for k, v in cols.items():
        m = l == k; rgb[m] = 0.55 * rgb[m] + 0.45 * np.array(v)
    return rgb.astype(np.uint8)
bz = np.where((lab == 4).any((1, 2)))[0]; zc = int(bz.mean()) if len(bz) else lab.shape[0]//2
by = np.where((lab == 4).any((0, 2)))[0]; yc = int(by.mean()); bx = np.where((lab == 4).any((0, 1)))[0]; xc = int(bx.mean())
ax = panel(ct[zc], lab[zc])[::-1]
sg = panel(ct[:, :, xc], lab[:, :, xc])[::-1]
co = panel(ct[:, yc, :], lab[:, yc, :])[::-1]
def fit(p, h=500):
    im = sitk.GetImageFromArray(p, isVector=True); s = h / p.shape[0]
    return sitk.GetArrayFromImage(sitk.Resample(im, [int(p.shape[1]*s), h], sitk.Transform(), sitk.sitkLinear, im.GetOrigin(), (1/s, 1/s), im.GetDirection(), 0)).astype(np.uint8)
ax2 = fit(ax); sg2 = fit(sg); co2 = fit(co)
sitk.WriteImage(sitk.GetImageFromArray(np.concatenate([ax2, sg2, co2], 1), isVector=True), f"{out}/{case}_labels_preview.png")
print(zc, yc, xc, ct.shape)
