---
tags: [service, script, python]
---

# list_part.py — PID/Name Lister

**Location:** `Code/list_part.py` (160 lines)
**Type:** standalone Python script
**Part of:** [[Architecture#Template Extraction Toolkit]]

## Purpose

Dumps every `*PART` entry (PID + name) from a THUMS LS-DYNA keyword file, following `*INCLUDE` chains automatically. Also reads HyperMesh `$HMNAME` comment annotations to recover human-readable part names where present. This is the reconnaissance tool used to figure out *which PIDs correspond to which anatomical structure* before anything gets extracted.

## Usage

```
python list_parts.py main_THUMS_AM50_V41.k
python list_parts.py main_THUMS_AM50_V41.k skull brain dura csf   # keyword filter
python list_parts.py main.k > all_parts.txt
```

## Inputs

- THUMS master `.k` file (`main_THUMS_AM50_V41.k`) plus everything it `*INCLUDE`s

## Outputs

- Console table of `PID | Name | Source file`
- `all_parts.txt` — the persisted master listing (kept as a [[Architecture#Data Assets|data asset]])

## Dependencies

- None (first tool in the toolchain — reads the raw reference template directly)

## Used by / feeds into

- [[extract_head]] and [[extract_head_right]] — the PID sets hardcoded in both scripts (`SKULL_CRANIAL_R`, `BRAIN`, `MENINGES_CSF`, etc.) were hand-curated by reading `all_parts.txt` output from this script
- [[count_elem]] — typically run alongside this script during the same PID-curation pass

## Notes

Shares its `parse_parts()` recursive `*INCLUDE`-following logic with the other toolkit scripts, though each script reimplements its own parser rather than importing a shared module.

[[Architecture|← Back to Architecture]]
