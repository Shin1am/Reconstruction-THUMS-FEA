---
tags: [service, notebook, converter]
---

# STL → VTK Converter

**Location:** `Code/STL_to_VTK_Converter.ipynb`
**Type:** Jupyter notebook
**Part of:** [[Architecture#Format Converters]]

## Purpose

Simple, lossless STL → VTK conversion. Preserves all vertex XYZ coordinates (float64), all triangle faces, and face normals. Works on binary and ASCII STL; duplicate vertices (which STL repeats per-triangle) are merged cleanly.

## Stages

| Cell | What it does |
|---|---|
| 1 | Install |
| 2 | Config — set paths |
| 3 | Convert STL → VTK |
| 4 | Validate + stats |

## Inputs

- `Data/ImageToStl.com_head_voxels.stl` — a segmented head-skin surface mesh (source: an external voxel-segmentation export tool, per the filename)

## Outputs

- `ImageToStl.com_head_voxels.vtu` in `Data/outputs/vtk_export/`

## Dependencies

- None (reads raw [[Architecture#Data Assets|Data assets]] directly)

## Used by / feeds into

- [[CT-MRI Registration - VTU-Mesh]] and [[VTU-VTU SyNRA Registration]] — both consume the resulting `.vtu` as the head-voxel-side mesh (fixed or moving, depending on notebook config)

[[Architecture|← Back to Architecture]]
