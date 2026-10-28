---
tags: [service, notebook, registration]
---

# CT/MRI Registration — VTU Mesh Version

**Location:** `Code/CT_MRI_Registration_VTU_Mesh.ipynb`
**Type:** Jupyter notebook (SimpleITK + PyVista, no ANTs)
**Part of:** [[Architecture#Registration Pipeline (SimpleITK)]]

## Purpose

The same 5-stage pipeline as [[CT-MRI Registration - Clean]] and [[CT-MRI Registration - K-Mesh]], but with `.vtu` mesh input/output throughout instead of `.k` — built for meshes that have already been converted out of the LS-DYNA keyword format.

## Stages (differences from [[CT-MRI Registration - Clean]])

| Cell | Stage | Notes |
|---|---|---|
| 3 | VTU reader & voxelizer | reads mesh via PyVista, voxelizes for registration |
| 5–8 | Preprocess / Rigid / Affine / Deformable | same stage sequence as the other two variants |
| 9 | **Apply transform to VTU mesh → new `.vtu`** | Builds the composite transform (initial → rigid → affine → deformable), warps every mesh point, saves a new `.vtu`. All original cell data, point data, and field data are preserved. Adds a `displacement_mm` point array for visualizing per-node movement in ParaView |
| 10 | Validation | alpha blend + checkerboard + Dice |

## Inputs

- `.vtu` mesh — designed to consume [[K to VTK Converter]] output (`Head_V6.vtu`) or [[STL to VTK Converter]] output (`ImageToStl.com_head_voxels.vtu`)
- Fixed CT/reference volume (`.nii.gz`)

## Outputs

- Registered `.vtu` mesh with preserved point/cell/field data plus a new `displacement_mm` field

## Dependencies

- [[K to VTK Converter]] and/or [[STL to VTK Converter]] — supplies the moving `.vtu` mesh (this notebook has no native `.k` parser, unlike [[CT-MRI Registration - K-Mesh]])
- Shares its core registration stage logic with [[CT-MRI Registration - Clean]]

## Used by / feeds into

- Alternative to [[VTU-VTU SyNRA Registration]] for the deformable stage — both consume the same `.vtu` inputs from the format converters, letting the team A/B the Demons vs. SyN deformable methods on identical input meshes
- [[k_mesh_qa]] does **not** currently parse `.vtu`, so post-warp QA for this notebook's output is not yet wired up (see [[k_mesh_qa]] notes)

[[Architecture|← Back to Architecture]]
