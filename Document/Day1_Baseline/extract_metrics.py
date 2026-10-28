"""Extract per-stage timing + metrics from the fresh run and diff against the frozen reference."""
import csv
import json
import re
from datetime import datetime as dt
from pathlib import Path

HERE = Path(__file__).parent
RUN = HERE / "rerun"

STAGES = {
    2: "Setup / imports",
    4: "Configuration",
    6: "Load template + extract skin surface",
    8: "Load subject point set (fallback surface)",
    10: "Stage 0   Center only",
    12: "Stage 0.5b Kabsch landmark seed",
    14: "Stage 0.5 Farthest-point sampling",
    16: "Stage 1   PCA pre-alignment (skipped)",
    18: "Stage 2   Rigid CPD",
    20: "Stage 3   Affine CPD + SV clamp",
    22: "Stage 4   Deformable CPD",
    24: "Stage 5   TPS (landmarks -> skin + whole mesh)",
    27: "Stage 6   Non-rigid ICP",
    29: "Stage 6.5 Confidence blend",
    31: "Stage 7   Validation table",
    32: "Stage 7   Bar plot",
    34: "Stage 5b  TPS rebuild + write .vtu",
    36: "QA       k_mesh_qa on written mesh",
}


def ts(s):
    return dt.fromisoformat(s.replace("Z", "+00:00"))


def timings(nb_path):
    nb = json.load(open(nb_path))
    out = {}
    for i, c in enumerate(nb["cells"]):
        ex = c.get("metadata", {}).get("execution", {})
        if c["cell_type"] == "code" and "iopub.execute_input" in ex:
            out[i] = (ts(ex["shell.execute_reply"]) - ts(ex["iopub.execute_input"])).total_seconds()
    return nb, out


def read_csv(p):
    return list(csv.DictReader(open(p)))


nb, t = timings(RUN / "scratch_executed.ipynb")
streams = {}
for i, c in enumerate(nb["cells"]):
    if c["cell_type"] == "code":
        for o in c.get("outputs", []):
            if o.get("output_type") == "stream":
                streams[i] = streams.get(i, "") + "".join(o["text"])
all_text = "\n".join(streams.values())

stage_rows = [{"cell": i, "stage": STAGES.get(i, f"cell {i}"), "seconds": round(s, 2)} for i, s in t.items()]
total = round(sum(t.values()), 1)

fresh = read_csv(RUN / "outputs" / "validation_summary_v2.csv")
ref = read_csv(HERE / "frozen" / "validation_summary_v2.csv")
max_abs_diff = 0.0
diffs = []
for a, b in zip(fresh, ref):
    for k in a:
        if k == "stage":
            continue
        d = abs(float(a[k]) - float(b[k]))
        max_abs_diff = max(max_abs_diff, d)
        if d > 0:
            diffs.append((a["stage"], k, float(a[k]), float(b[k])))

qa_inv = int(re.search(r"Inverted elements \(negative volume\):\s*(\d+)", all_text).group(1))
qa_deg = int(re.search(r"Near-zero volume \(degenerate\)\s*:\s*(\d+)", all_text).group(1))
ratio = re.search(r"Max/min volume ratio.*?:\s*([\d.e+]+)", all_text).group(1)
versions = dict(re.findall(r"^(pyvista|numpy)\s*:\s*(\S+)", all_text, flags=re.M))

metrics = {
    "run_utc": dt.utcnow().isoformat() + "Z",
    "per_cell_seconds": stage_rows,
    "total_seconds_sum_of_cells": total,
    "validation_fresh": fresh,
    "validation_reference": ref,
    "max_abs_diff_vs_reference": max_abs_diff,
    "diffs_vs_reference": diffs,
    "qa": {"inverted": qa_inv, "degenerate": qa_deg, "total_solids": 176441,
           "inverted_pct": round(100 * qa_inv / 176441, 3), "max_min_volume_ratio": ratio},
    "reported_versions": versions,
}
json.dump(metrics, open(HERE / "baseline_metrics.json", "w"), indent=2)

print(f"{'cell':>4}  {'seconds':>8}  stage")
for r in stage_rows:
    print(f"{r['cell']:>4}  {r['seconds']:>8.2f}  {r['stage']}")
print(f"total (sum of cell times): {total} s")
print(f"max |fresh - reference| over all validation columns: {max_abs_diff}")
for d in diffs[:20]:
    print("DIFF", d)
print(f"QA fresh: inverted={qa_inv} degenerate={qa_deg} ratio={ratio}")
print("versions:", versions)
print("final:", fresh[0]["stage"], fresh[0]["hausdorff"], "->", fresh[-1]["stage"], fresh[-1]["hausdorff"])
