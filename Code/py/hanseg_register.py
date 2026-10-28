"""Rigid MR->CT registration (Mattes MI) for a HaN-Seg case. usage: hanseg_register.py case_XX outdir"""
import SimpleITK as sitk, sys, os, numpy as np
root = r"D:/2d_3d_regis dataset/New_version/Data/HaN-Seg/HaN-Seg/HaN-Seg/set_1"
case, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
ct = sitk.ReadImage(f"{root}/{case}/{case}_IMG_CT.nrrd", sitk.sitkFloat32)
mr = sitk.ReadImage(f"{root}/{case}/{case}_IMG_MR_T1.nrrd", sitk.sitkFloat32)
# head extent in CT (body mask) for reporting
a = sitk.GetArrayFromImage(ct); print(case, "CT HU range", a.min(), a.max())
_m = sitk.GetArrayFromImage(mr); offset_fixed = bool(_m.min() >= 30000)
if offset_fixed:
    mr = sitk.Cast(sitk.Clamp(mr - 32768.0, sitk.sitkFloat32, 0.0, 1e9), sitk.sitkFloat32); print("MR +32768 offset removed")
# downsample CT for speed
ctd = sitk.Shrink(sitk.SmoothingRecursiveGaussian(ct, 1.0), [3, 3, 1])
mrd = sitk.Shrink(mr, [2, 2, 1])
best = None
# initial: align centers of mass of body (CT>-300, MR>thresh) + try several z-shifts since frames differ
def body_centroid(img, thr):
    m = sitk.BinaryThreshold(img, float(thr), 1e9, 1, 0)
    f = sitk.LabelShapeStatisticsImageFilter(); f.Execute(m); return np.array(f.GetCentroid(1))
cc = body_centroid(ctd, -300)
mt = float(np.percentile(sitk.GetArrayFromImage(mrd), 60))
mc = body_centroid(mrd, mt)
print("centroids", cc, mc)
for dz in (0, -40, 40):
    t = sitk.TranslationTransform(3, tuple(mc - cc + np.array([0, 0, dz]) * -1))  # fixed->moving: p_mov = p_fix + (mc-cc)
    t = sitk.TranslationTransform(3, tuple((mc - cc) + np.array([0, 0, dz])))
    init = sitk.Euler3DTransform(); init.SetTranslation(t.GetOffset())
    R = sitk.ImageRegistrationMethod()
    R.SetMetricAsMattesMutualInformation(50)
    R.SetMetricSamplingStrategy(R.RANDOM); R.SetMetricSamplingPercentage(0.15, 42)
    R.SetInterpolator(sitk.sitkLinear)
    R.SetOptimizerAsRegularStepGradientDescent(2.0, 1e-3, 200, relaxationFactor=0.6)
    R.SetOptimizerScalesFromPhysicalShift()
    R.SetShrinkFactorsPerLevel([4, 2, 1]); R.SetSmoothingSigmasPerLevel([3, 2, 1])
    R.SetInitialTransform(init, inPlace=False)
    T = R.Execute(ctd, mrd)
    v = R.GetMetricValue(); print("dz", dz, "metric", v, "params", T.GetParameters())
    if best is None or v < best[0]: best = (v, T)
sitk.WriteTransform(best[1], f"{out}/{case}_mr2ct.tfm")
res = sitk.Resample(mr, ct, best[1], sitk.sitkLinear, 0.0)
sitk.WriteImage(res, f"{out}/{case}_MR_in_CT.nii.gz")
print("best metric", best[0])
import json, math
p = best[1].GetParameters(); rot = [math.degrees(x) for x in p[:3]]
json.dump({"metric": float(best[0]), "rot_deg": rot, "trans_mm": list(p[3:]), "mr_offset_fixed": offset_fixed}, open(f"{out}/reg_qa.json", "w"))
