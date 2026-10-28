"""QA flags + export of the ground-truth model for one HaN-Seg case.
usage: hanseg_gt_qa_export.py case_XX
Writes GT/<usable|not_usable>/<case>/ with STL surfaces (LPS mm), label NIfTIs, report.json. Prints STATUS line."""
import sys, os, json, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, SimpleITK as sitk, vtk
from vtk.util import numpy_support as ns
from scipy import ndimage as ndi
case = sys.argv[1]
ROOT = r"D:/2d_3d_regis dataset/New_version"
SET = f"{ROOT}/Data/HaN-Seg/HaN-Seg/HaN-Seg/set_1"
GT = f"{ROOT}/Data/HaN-Seg/GT"; W = f"{ROOT}/outputs/hanseg_{case}"; H = 0.8
fails, warns, info = [], [], {}
s2_drop_vent = False

def rd(name, must=True):
    p = f"{W}/{case}_{name}"
    if not os.path.exists(p):
        if must: fails.append(f"missing output {name} (pipeline stage crashed)")
        return None
    return sitk.ReadImage(p)

nested_im = rd("nested_labels.nii.gz")
oar_im = rd("oar_labels.nii.gz"); fac_im = rd("facial_labels.nii.gz"); s2_im = rd("stage2_labels.nii.gz"); s3_im = rd("stage3_labels.nii.gz")
arr = lambda im: sitk.GetArrayFromImage(im) if im is not None else None
lab, oar, fac, s2, s3 = map(arr, (nested_im, oar_im, fac_im, s2_im, s3_im))
vox = H**3 / 1000.0
reg = json.load(open(f"{W}/reg_qa.json")) if os.path.exists(f"{W}/reg_qa.json") else {}
info["registration"] = reg
if not reg: fails.append("no registration result")
else:
    if max(abs(x) for x in reg["rot_deg"]) > 15: warns.append(f"large MR->CT rotation {max(abs(x) for x in reg['rot_deg']):.1f} deg")
    if reg["mr_offset_fixed"]: warns.append("MR had +32768 offset (corrected)")

# ---- acquisition quality
rdr = sitk.ImageFileReader(); rdr.SetFileName(f"{SET}/{case}/{case}_IMG_CT.nrrd"); rdr.ReadImageInformation()
ctsp, ctsz, cto = rdr.GetSpacing(), rdr.GetSize(), rdr.GetOrigin(); info["ct_spacing"] = list(ctsp); info["ct_z_range"] = [cto[2], cto[2] + ctsp[2] * ctsz[2]]
if ctsp[2] > 2.5: warns.append(f"thick CT slices ({ctsp[2]:.1f} mm)")
if ctsp[0] > 1.0: warns.append(f"coarse CT pixels ({ctsp[0]:.2f} mm)")
rm = sitk.ImageFileReader(); rm.SetFileName(f"{SET}/{case}/{case}_IMG_MR_T1.nrrd"); rm.ReadImageInformation()
if rm.GetSpacing()[2] > 3.5: warns.append(f"thick MR slices ({rm.GetSpacing()[2]:.1f} mm)")

if lab is not None:
    org = np.array(nested_im.GetOrigin()); Z = lab.shape[0]
    head = lab > 0; brain = lab == 4; skull = lab == 2; cav = (lab == 3) | brain
    v = lambda m: float(m.sum() * vox)
    info["volumes_mL"] = {"skin_head": v(head), "skull": v(skull), "csf_shell": v(lab == 3), "brain": v(brain)}
    ztop_ct = cto[2] + ctsp[2] * ctsz[2]; grid_top = org[2] + Z * H
    if grid_top > ztop_ct - 2: fails.append("CT truncates the top of the head (vertex not covered)")
    if head[-3:].any(): warns.append("skin touches the grid top (vertex margin small)")
    if v(brain) < 800 or v(brain) > 2000: fails.append(f"brain volume implausible ({v(brain):.0f} mL)")
    elif v(brain) < 1000 or v(brain) > 1700: warns.append(f"brain volume unusual ({v(brain):.0f} mL)")
    if v(skull) < 300: fails.append(f"skull volume too small ({v(skull):.0f} mL)")
    thick = float(np.median(ndi.distance_transform_edt(skull, sampling=H)[skull]) * 2) if skull.any() else 0.0
    info["skull_thickness_proxy_mm"] = thick
    if thick < 1.5 or thick > 12: fails.append(f"skull thickness implausible ({thick:.1f} mm)")
    elif thick < 2.5 or thick > 8: warns.append(f"skull thickness unusual ({thick:.1f} mm)")
    if (brain & skull).any() or (brain & (lab == 3)).any(): fails.append("nesting violated (brain overlaps skull/shell)")
    try:
        mr_h = sitk.ReadImage(f"{W}/{case}_MR_head.nii.gz"); tfm = sitk.ReadTransform(f"{W}/{case}_mr2ct.tfm")
        mr0 = sitk.ReadImage(f"{SET}/{case}/{case}_IMG_MR_T1.nrrd", sitk.sitkFloat32)
        one = sitk.Cast(mr0 * 0 + 1, sitk.sitkUInt8)
        fov = sitk.GetArrayFromImage(sitk.Resample(one, nested_im, tfm, sitk.sitkNearestNeighbor, 0)) > 0
        mr = sitk.GetArrayFromImage(mr_h)
        cov = float((brain & fov).sum() / max(1, brain.sum())); info["mr_brain_coverage"] = cov
        if cov < 0.9: warns.append(f"MR covers only {cov*100:.0f}% of the brain: MR-derived interior (ventricles) unreliable; CT-based skin/skull/face/brain unaffected")
        thr = 0.15 * np.percentile(mr[fov & head], 99) if (fov & head).any() else 1
        mrh = ndi.binary_opening(ndi.gaussian_filter(mr, 1.0) > thr, iterations=2)
        l, n = ndi.label(mrh & fov); mrh = (l == (np.argmax(np.bincount(l.ravel())[1:]) + 1)) if n else mrh
        a_, b_ = head & fov, mrh & fov
        dice = float(2 * (a_ & b_).sum() / max(1, a_.sum() + b_.sum())); info["mr_ct_head_dice"] = dice
        if dice < 0.7: fails.append(f"MR/CT head overlap poor (Dice {dice:.2f}) - likely mis-registered")
        elif dice < 0.85: warns.append(f"MR/CT head overlap moderate (Dice {dice:.2f})")
    except Exception as e:
        fails.append(f"MR QA error: {e}")
    if fac is not None:
        fv = {n: v(fac == L) for L, n in ((10, "maxilla"), (11, "zygomatic"), (12, "nasal"), (13, "mandible_ct"), (14, "teeth"), (15, "facial_other"))}; info["facial_mL"] = fv
        if fv["maxilla"] < 15: warns.append(f"maxilla small ({fv['maxilla']:.0f} mL)")
        if fv["mandible_ct"] < 30: fails.append(f"mandible missing/small ({fv['mandible_ct']:.0f} mL)")
        if fv["nasal"] < 3: warns.append("nasal bones tiny/missing")
        if fv["teeth"] < 5: warns.append("teeth not separable in this CT")
    if s2 is not None:
        sv = {"ventricles": v(s2 == 20), "cerebellum": v(s2 == 21), "cerebrum": v(s2 == 22)}; info["stage2_mL"] = sv
        if sv["cerebellum"] < 80 or sv["cerebellum"] > 260: warns.append(f"cerebellum volume unusual ({sv['cerebellum']:.0f} mL)")
        if sv["ventricles"] < 3:
            warns.append(f"ventricles not reliable ({sv['ventricles']:.1f} mL, MR does not cover them): ventricle surface NOT exported"); info["ventricles_reliable"] = False; s2_drop_vent = True
        elif sv["ventricles"] > 150: warns.append(f"ventricle volume unusual ({sv['ventricles']:.0f} mL)")

status = "not_usable" if fails else "usable"
out = f"{GT}/{status}/{case}"
for other in ("usable", "not_usable"):
    if other != status and os.path.isdir(f"{GT}/{other}/{case}"): shutil.rmtree(f"{GT}/{other}/{case}")
if os.path.isdir(out): shutil.rmtree(out)
os.makedirs(f"{out}/stl"); os.makedirs(f"{out}/labels")

def to_stl(mask, path, tris=80000):
    if mask is None or mask.sum() < 200: return False
    l, n = ndi.label(mask)
    if n > 1:
        sz = np.bincount(l.ravel()); sz[0] = 0; keep = sz >= max(50, 0.02 * sz.max()); keep[0] = False; mask = keep[l]
    f = ndi.gaussian_filter(mask.astype(np.float32), 0.7)
    img = vtk.vtkImageData(); Z_, Y_, X_ = f.shape; img.SetDimensions(X_, Y_, Z_); img.SetSpacing(H, H, H); img.SetOrigin(*nested_im.GetOrigin())
    img.GetPointData().SetScalars(ns.numpy_to_vtk(f.ravel(), deep=True, array_type=vtk.VTK_FLOAT))
    fe = vtk.vtkFlyingEdges3D(); fe.SetInputData(img); fe.SetValue(0, 0.5); fe.ComputeNormalsOff(); fe.Update()
    sm = vtk.vtkWindowedSincPolyDataFilter(); sm.SetInputConnection(fe.GetOutputPort()); sm.SetNumberOfIterations(15); sm.SetPassBand(0.1); sm.NormalizeCoordinatesOn(); sm.Update()
    poly = sm.GetOutput()
    if poly.GetNumberOfCells() > tris:
        dc = vtk.vtkQuadricDecimation(); dc.SetInputData(poly); dc.SetTargetReduction(1 - tris / poly.GetNumberOfCells()); dc.Update(); poly = dc.GetOutput()
    w = vtk.vtkSTLWriter(); w.SetFileName(path); w.SetInputData(poly); w.SetFileTypeToBinary(); w.Write(); return True

if lab is not None:
    surf = {"skin_surface": lab > 0, "outer_table_surface": (lab >= 2), "inner_table_surface": cav, "brain": brain, "skull_cranium": lab == 2, "csf_shell": lab == 3}
    if oar is not None: surf.update({"brainstem_OAR": oar == 5, "eyes_OAR": oar == 6, "mandible_OAR": oar == 7, "optic_nerves_chiasm_OAR": oar == 8, "cochleae_OAR": oar == 9})
    if fac is not None: surf.update({"maxilla_palate_alveolar": fac == 10, "zygomatic": fac == 11, "nasal_bones": fac == 12, "mandible_bone": fac == 13, "teeth": fac == 14, "facial_other_bone": fac == 15})
    if s2 is not None:
        surf.update({"cerebellum_approx": s2 == 21, "cerebrum_approx": s2 == 22})
        if not s2_drop_vent: surf["ventricles"] = s2 == 20
    if s3 is not None:
        surf.update({"dura_approx": s3 == 30, "tentorium_approx": s3 == 32})
        if s2_drop_vent: warns.append("falx surface NOT exported (its lower edge is anchored on the ventricles)")
        else: surf["falx_approx"] = s3 == 31
    done = []
    for k, m in surf.items():
        try:
            if to_stl(m, f"{out}/stl/{case}_{k}.stl"): done.append(k)
        except Exception as e: warns.append(f"STL export failed for {k}: {e}")
    info["stl_exported"] = done
    for name, im in (("nested_labels", nested_im), ("oar_labels", oar_im), ("facial_labels", fac_im), ("stage2_labels", s2_im), ("stage3_labels", s3_im)):
        if im is not None: sitk.WriteImage(im, f"{out}/labels/{case}_{name}.nii.gz", True)
    for n in ("label_names.json", "stage2_names.json", "stage3_names.json", f"{case}_mr2ct.tfm"):
        p = f"{W}/{n}"
        if os.path.exists(p): shutil.copy(p, f"{out}/labels/{n}")
    info["grid"] = {"origin_LPS_mm": list(nested_im.GetOrigin()), "spacing_mm": H, "size_xyz": list(nested_im.GetSize())}

rep = {"case": case, "status": status, "fail_reasons": fails, "warnings": warns, "details": info,
       "coordinate_system": "LPS mm, CT physical space of the original HaN-Seg CT. STL vertices are in this frame. Label NIfTIs share one 0.8 mm grid."}
json.dump(rep, open(f"{out}/report.json", "w"), indent=1)
print(f"STATUS {case} {status} | fails={fails} | warns={warns}")
