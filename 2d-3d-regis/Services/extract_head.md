---
tags: [service, script, python]
---

# extract_head.py — Head-Only Extractor

**Location:** `Code/extract_head.py` (565 lines)
**Type:** standalone Python script
**Part of:** [[Architecture#Template Extraction Toolkit]]

## Purpose

The main extractor. Reads the full-body THUMS AM50 V4.1 keyword file (following every `*INCLUDE`), filters down to a target set of head-region PIDs, automatically pulls in every referenced `*MAT`/`*SECTION`/`*EOS`/`*HOURGLASS` card, and writes a **self-contained** `.k` file (no external includes needed) ready for LS-DYNA Student.

## Usage

```
python extract_head.py main_THUMS_AM50_V41.k
python extract_head.py main_THUMS_AM50_V41.k --minimal
python extract_head.py main_THUMS_AM50_V41.k --skin
python extract_head.py main_THUMS_AM50_V41.k --output my_head.k
```

## Modes

| Mode | PIDs included |
|---|---|
| default | skull + brain + meninges/CSF + head skin + connectors |
| `--minimal` | skull + brain + meninges/CSF only (safest for 128K cap) |
| `--skin` | head skin only (excludes connectors) |

## PID sets (hardcoded, curated via [[list_part]])

- `SKULL_CRANIAL_R` / `SKULL_CRANIAL_L`: `88000001`–`88000099`
- `BRAIN`: `88000100`–`88000105` (R), `88000120`–`88000125` (L)
- `MENINGES_CSF`: CSF layers, ventricles, pia, arachnoid, tentorium, dura, falx, superior sagittal sinus — `88000106`–`88000142`, `88000242`–`88000255`

## Inputs

- THUMS master `.k` file, following `*INCLUDE` chains
- Target PID list (see above), sized using [[count_elem]]

## Outputs

- `Head_V6.k` (default mode)
- `Head_V6_head_only.k` (head-only)
- `Head_V6_head_skin.k` (`--skin` mode)

## Dependencies

- [[Architecture#Reference Template — THUMS AM50|THUMS reference template]] (raw input)
- [[list_part]] — used beforehand to identify/verify PIDs
- [[count_elem]] — used beforehand to confirm the PID set stays under the 128K cap

## Used by / feeds into

- [[k_mesh_qa]] — every extractor output must be run through the QA gate before use
- [[CT-MRI Registration - K-Mesh]] — consumes `Head_V6*.k` as the "moving" mesh to be registered
- [[K to VTK Converter]] — converts `Head_V6.k` to `.vtu` for the VTU-based notebooks ([[CT-MRI Registration - VTU-Mesh]], [[VTU-VTU SyNRA Registration]])

## Known issue (from project handoff)

The `--minimal` mode originally used the full facial skeleton PID range and produced 167,986 nodes — over the 128K cap. Fix in progress: restrict skull PIDs to cranial-vault-only (frontal/parietal/temporal/occipital/sphenoid/ethmoid), dropping facial bones (lacrimal/nasal/zygomatic/maxilla/mandible/palatine/teeth) that aren't relevant to intracranial deformation.

[[Architecture|← Back to Architecture]]
