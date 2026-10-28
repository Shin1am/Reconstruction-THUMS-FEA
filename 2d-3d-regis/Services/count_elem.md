---
tags: [service, script, python]
---

# count_elem.py — Per-PID Element Counter

**Location:** `Code/count_elem.py` (219 lines)
**Type:** standalone Python script
**Part of:** [[Architecture#Template Extraction Toolkit]]

## Purpose

Counts elements per PID across a `.k` file, so the team can see exactly which parts to drop to fit under the **LS-DYNA Student 128K node/element cap**. This is the budgeting tool used before/alongside a real extraction run.

## Usage

```
python count_elements.py Head_V6.k
python count_elements.py Head_V6.k --top 20
python count_elements.py Head_V6.k --shells-only
```

## Inputs

- Any `.k` file — either the raw THUMS reference or an already-extracted output such as `Head_V6.k`

## Outputs

- Console report of element counts per PID (optionally filtered/sorted)

## Dependencies

- None directly, but is normally run against the [[Architecture#Reference Template — THUMS AM50|THUMS reference template]] or against output from [[extract_head]] / [[extract_head_right]] to check whether a candidate PID set fits the 128K cap

## Used by / feeds into

- [[extract_head]] and [[extract_head_right]] — informed the decision documented in the project handoff to switch from "full facial skeleton" (167K nodes, over cap) to "cranial-vault-only" skull PIDs (~80–110K nodes, under cap)

[[Architecture|← Back to Architecture]]
