---
tags: [service, script, python]
---

# extract_head_right.py — Right-Hemisphere Extractor

**Location:** `Code/extract_head_right.py` (501 lines)
**Type:** standalone Python script
**Part of:** [[Architecture#Template Extraction Toolkit]]

## Purpose

A specialized, more aggressive variant of [[extract_head]] aimed squarely at fitting under the LS-DYNA Student R16.1 **128K element cap**. Extracts right-side skull + brain + essential meninges only.

## Strategy

- Keep **all** right-side brain (white/gray matter, cerebellum, brainstem)
- Keep **all** right-side CSF layers
- Keep **right cranial vault bones only** (no facial skeleton)
- Keep bilateral **midline structures** (falx, superior sagittal sinus) — dropping these creates an open contact boundary that destabilizes the solve
- Drop: all `_L`/`_l` parts, eyes, face muscles, jaw, skin, connector elements
- Deletes 4 known degenerate elements in `CSF_Stem_R`/`CSF_Stem_L`

## Usage

```
python extract_right_hemi.py Head_V6.k
python extract_right_hemi.py Head_V6.k --output my_output.k
```

## Inputs

- A `.k` file (typically `Head_V6.k`, already produced by [[extract_head]])

## Outputs

- `Head_V6_right_hemi.k`

## Dependencies

- [[extract_head]] — typically run on its output rather than the raw THUMS master file
- [[list_part]] / [[count_elem]] — same PID-curation workflow as [[extract_head]]

## Used by / feeds into

- [[k_mesh_qa]] — validates the output, including the manually-patched degenerate CSF elements

[[Architecture|← Back to Architecture]]
