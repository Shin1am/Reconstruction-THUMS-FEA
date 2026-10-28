import SimpleITK as sitk, sys, numpy as np
root = r"D:/2d_3d_regis dataset/New_version/Data/HaN-Seg/HaN-Seg/HaN-Seg/set_1"
case = sys.argv[1]; out = f"D:/2d_3d_regis dataset/New_version/outputs/hanseg_{case}"
ct = sitk.ReadImage(f"{root}/{case}/{case}_IMG_CT.nrrd", sitk.sitkFloat32)
mr = sitk.ReadImage(f"{out}/{case}_MR_in_CT.nii.gz")
a = sitk.GetArrayFromImage(ct); m = sitk.GetArrayFromImage(mr)
def norm(x, lo, hi): return (np.clip((x - lo) / (hi - lo), 0, 1) * 255).astype(np.uint8)
x = a.shape[2] // 2
c = a[:, :, x][::-1]; mm = m[:, :, x][::-1]
mv = np.percentile(m[m > 0], 90) * 1.8
sp = ct.GetSpacing()
def rs(img): return np.repeat(img, int(round(sp[2] / sp[0] * 1)) or 1, axis=0) if False else img
ct8 = norm(c, -200, 400); mr8 = norm(mm, 0, mv)
ov = np.stack([ct8, np.maximum(ct8 // 2, mr8), ct8 // 2], -1)  # CT gray-ish, MR green
rowscale = sp[2] / sp[0]
def stretch(img):
    img = sitk.GetImageFromArray(img, isVector=img.ndim == 3)
    img.SetSpacing((1, rowscale))
    n = [img.GetSize()[0], int(img.GetSize()[1] * rowscale)]
    return sitk.Resample(img, n, sitk.Transform(), sitk.sitkLinear, img.GetOrigin(), (1, 1), img.GetDirection(), 0)
panel = np.concatenate([sitk.GetArrayFromImage(stretch(np.stack([ct8]*3, -1))), sitk.GetArrayFromImage(stretch(np.stack([mr8]*3, -1))), sitk.GetArrayFromImage(stretch(ov))], 1).astype(np.uint8)
sitk.WriteImage(sitk.GetImageFromArray(panel, isVector=True), f"{out}/{case}_sagittal.png")
print(panel.shape)
