# External reconstruction validation

Inputs required: independently acquired RGB photograph(s) and intact CT/MRI of the SAME participant, with provider-supplied pairing. No impact/video-motion work. No CT-derived renders as practical 2D input. THUMS morphing results are not SAM3D validation.

## Data candidates checked
- BFSM/Vision Tomography: https://github.com/wang-zidu/BFSM ; https://arxiv.org/html/2509.24577v1 . Paper reports >200 paired CT skull/face and textured face scans. Optical scan coverage is ear-to-ear, hairline-to-neck, not whole scalp. Raw RGB photographs, original medical volumes, pairing manifest and access must be confirmed. Rendered textured scans are a separate synthetic-input experiment.
- CBU MRI/photo study: https://www.mdpi.com/2306-5354/9/10/591 . Reports 10 volunteers with MRI and actual photos. BioFIND access statement does not establish that these 10 volunteers' photographs are released. Need confirmation from provider.
- NoW: https://now.is.tue.mpg.de/dataset.html . Photos and optical 3D scans; not a CT/MRI dataset. Suitable only for a separate external benchmark.

No fully verified, downloadable paired RGB + intact CT/MRI dataset has yet been acquired. Existing local case_02 contains CT-derived skin surfaces but no verified matching RGB input or raw CT/MRI volume.

## Protocol
1. Preserve original image, acquisition time, subject pairing, CT voxel affine, units, coordinate system and coverage metadata.
2. Segment skin/scalp from CT; exclude table, supports, background; inspect masks in all planes. Save mask plus STL/VTP/PLY in physical mm. Preserve CT and internal structures for later work. No segmentation has been newly performed in this validation task.
3. Reconstruct from RGB only using a pinned SAM3D version/checkpoint. Preserve raw output. Log cleanup and crop rules; do not reshape scalp to CT or silently delete high-error areas. Hair is not scalp: report observable face ROI separately from inferred/occluded scalp.
4. Initialize with independently identified paired landmarks; proper rotation (det R=+1), translation only. Refine with rigid ICP only. No affine, TPS, non-rigid CPD or deformable ICP.
5. If metric scale is unknown, report a separate similarity-aligned experiment with ONE isotropic scale factor. Record scale and whether it came from independent calibration or GT fitting; GT-fitted scale does not validate absolute size.
6. Freeze common anatomical ROI before evaluation. Report full available coverage and ROI coverage. Use area-uniform surface samples and point-to-triangle distances in both directions.
7. Mean symmetric distance = (mean d_AB + mean d_BA)/2. Symmetric RMSE = sqrt((mean d_AB^2 + mean d_BA^2)/2). Chamfer-L1 = mean d_AB + mean d_BA (mm); explicitly state convention. HD95 = max(P95 d_AB, P95 d_BA). Heatmaps retain all errors, with color clipping labeled. Save transform, aligned mesh, metric JSON and sampling seed.

## Execution prerequisites
Local environment inspected: macOS arm64; numpy/scipy/pyvista available; torch, nibabel, SimpleITK absent. Official SAM3D Objects setup calls for Linux and NVIDIA GPU >=32 GB VRAM and approved checkpoint access: https://github.com/facebookresearch/sam-3d-objects/blob/main/doc/setup.md . No inference has been run. Need verified paired input and an available inference environment before proceeding to measured research results.

## Follow-up file-level audit
BFSM repository tree and sample README inspected directly. sample_001 includes original CT face.obj/skull.obj and textured scanner face_scan.obj/mtl/png. face_scan.png is a mesh texture, not verified raw camera photograph. The sample README explicitly states image_clinical/1.png is a separate photograph-only demonstration WITHOUT CT; image_portrait/2.jpg is an Isaac Newton painting. Therefore neither demonstration image can be paired with sample_001 CT for this experiment. Provenance files saved alongside this report.

CBU repository tree inspected: Experiment 1 contains behavioral CSV and R analysis code only. No photographic inputs or MRI volumes were found in that repository tree. Provider data access remains required.
