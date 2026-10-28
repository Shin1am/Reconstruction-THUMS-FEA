# Run inside Slicer: Slicer.exe --no-main-window --python-script hanseg_build_scene.py
import slicer, numpy as np, SimpleITK as sitk, sitkUtils, os, json
case = "case_02"; out = f"D:/2d_3d_regis dataset/New_version/outputs/hanseg_{case}"
names = {int(k): v for k, v in json.load(open(f"{out}/label_names.json")).items()}
ct = slicer.util.loadVolume(f"{out}/{case}_CT_HU_head.nii.gz"); ct.SetName("CT_HU")
mr = slicer.util.loadVolume(f"{out}/{case}_MR_head.nii.gz"); mr.SetName("MR_T1_registered")
nested = sitk.ReadImage(f"{out}/{case}_nested_labels.nii.gz"); oar = sitk.ReadImage(f"{out}/{case}_oar_labels.nii.gz")
na = sitk.GetArrayFromImage(nested)
def lm(arr, name):
    im = sitk.GetImageFromArray(arr.astype(np.uint8)); im.CopyInformation(nested)
    node = sitkUtils.PushVolumeToSlicer(im, name=name, className="vtkMRMLLabelMapVolumeNode"); return node
seg = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", f"HaN-Seg_{case}_head")
seg.CreateDefaultDisplayNodes(); seg.SetReferenceImageGeometryParameterFromVolumeNode(ct)
colors = {"Skin_surface": (0.95, 0.75, 0.6), "Skull": (0.95, 0.95, 0.9), "CSF_meninges_shell": (0.3, 0.6, 1.0), "Brain": (0.9, 0.35, 0.35)}
def add(arr, segname, color):
    node = lm(arr, "tmp_" + segname)
    slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(node, seg)
    sid = seg.GetSegmentation().GetNthSegmentID(seg.GetSegmentation().GetNumberOfSegments() - 1)
    s = seg.GetSegmentation().GetSegment(sid); s.SetName(segname); s.SetColor(*color)
    slicer.mrmlScene.RemoveNode(node)
add((na > 0), "Skin_surface", colors["Skin_surface"])
add((na == 2), "Skull", colors["Skull"]); add((na == 3), "CSF_meninges_shell", colors["CSF_meninges_shell"]); add((na == 4), "Brain", colors["Brain"])
oa = sitk.GetArrayFromImage(oar)
oc = {5: (0.9, 0.7, 0.2), 6: (0.2, 0.8, 0.3), 7: (0.8, 0.8, 0.6), 8: (1, 1, 0), 9: (0.6, 0.2, 0.8)}
for L in range(5, 10):
    if (oa == L).any(): add(oa == L, names[L], oc[L])
import os as _os
_fp = f"{out}/{case}_facial_labels.nii.gz"
if _os.path.exists(_fp):
    fa = sitk.GetArrayFromImage(sitk.ReadImage(_fp))
    fcol = {10: (1, .6, 0), 11: (0, .85, 0), 12: (1, 0, 1), 13: (0, .85, 1), 14: (1, 1, 0), 15: (.67, .47, .24)}
    for L in range(10, 16):
        if (fa == L).sum() > 50: add(fa == L, names[L], fcol[L])
_sp = f"{out}/{case}_stage2_labels.nii.gz"
if _os.path.exists(_sp):
    s2 = sitk.GetArrayFromImage(sitk.ReadImage(_sp)); n2 = json.load(open(f"{out}/stage2_names.json"))
    for k, v in n2.items():
        if (s2 == int(k)).sum() > 50: add(s2 == int(k), v["name"], tuple(v["color"]))
_tp = f"{out}/{case}_stage3_labels.nii.gz"
if _os.path.exists(_tp):
    s3 = sitk.GetArrayFromImage(sitk.ReadImage(_tp)); n3 = json.load(open(f"{out}/stage3_names.json"))
    for k, v in n3.items():
        if (s3 == int(k)).sum() > 50: add(s3 == int(k), v["name"], tuple(v["color"]))
seg.CreateClosedSurfaceRepresentation()
d = seg.GetDisplayNode(); d.SetVisibility3D(True)
d.SetSegmentOpacity3D(seg.GetSegmentation().GetSegmentIdBySegmentName("Skin_surface"), 0.25)
d.SetSegmentOpacity3D(seg.GetSegmentation().GetSegmentIdBySegmentName("Skull"), 0.5)
# windows
ct.GetDisplayNode().SetAutoWindowLevel(False); ct.GetDisplayNode().SetWindowLevel(1500, 300)
mr.GetDisplayNode().SetAutoWindowLevel(True)
lay = slicer.app.layoutManager()
if lay: lay.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
for n in (("Red", "Green", "Yellow") if lay else ()):
    c = lay.sliceWidget(n).mrmlSliceNode(); lay.sliceWidget(n).sliceLogic().GetSliceCompositeNode().SetBackgroundVolumeID(ct.GetID())
    lay.sliceWidget(n).sliceLogic().GetSliceCompositeNode().SetForegroundVolumeID(mr.GetID()); lay.sliceWidget(n).sliceLogic().GetSliceCompositeNode().SetForegroundOpacity(0.0)
if lay: lay.threeDWidget(0).threeDView().resetFocalPoint()
# STLs
os.makedirs(f"{out}/stl", exist_ok=True)
slicer.vtkSlicerSegmentationsModuleLogic.ExportSegmentsClosedSurfaceRepresentationToFiles(f"{out}/stl", seg, None, "STL", True, 1.0, False)
# save
seg_out = f"{out}/{case}_segmentation.seg.nrrd"; slicer.util.saveNode(seg, seg_out)
slicer.util.saveScene(f"{out}/{case}_head_ground_truth.mrb")
# screenshot
slicer.app.processEvents()
try:
    assert lay
    import vtk
    w = vtk.vtkWindowToImageFilter(); w.SetInput(lay.threeDWidget(0).threeDView().renderWindow()); w.Update()
    p = vtk.vtkPNGWriter(); p.SetFileName(f"{out}/{case}_3d.png"); p.SetInputConnection(w.GetOutputPort()); p.Write()
except Exception as e: print("screenshot failed", e)
print("SCENE_DONE"); slicer.app.quit()
