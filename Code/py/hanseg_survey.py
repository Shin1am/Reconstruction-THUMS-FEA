import SimpleITK as sitk, glob, os, csv, sys
root = r"D:/2d_3d_regis dataset/New_version/Data/HaN-Seg/HaN-Seg/HaN-Seg/set_1"
rows = []
for d in sorted(glob.glob(root + "/case_*")):
    c = os.path.basename(d)
    r = {"case": c}
    for k, suf in (("ct", "IMG_CT"), ("mr", "IMG_MR_T1")):
        rd = sitk.ImageFileReader(); rd.SetFileName(f"{d}/{c}_{suf}.nrrd"); rd.ReadImageInformation()
        sz, sp, o = rd.GetSize(), rd.GetSpacing(), rd.GetOrigin()
        r[k + "_size"] = "x".join(map(str, sz))
        r[k + "_sp"] = "x".join(f"{s:.2f}" for s in sp)
        r[k + "_z0"] = round(o[2]); r[k + "_z1"] = round(o[2] + sp[2] * sz[2])
        r[k + "_zlen"] = round(sp[2] * sz[2])
    rows.append(r)
w = csv.DictWriter(sys.stdout, rows[0].keys(), lineterminator="\n"); w.writeheader(); w.writerows(rows)
