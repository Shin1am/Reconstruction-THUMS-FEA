"""Make a throw-away copy of the frozen notebook for a fresh, non-destructive run.

Only I/O plumbing is changed (BASE_DIR, OUTPUT_DIR, the `!pip install` line).
No algorithm, parameter, or seed is touched. Saved outputs are cleared so the
executed copy contains only results from the fresh run.
"""
import json
import re
import sys

src, dst, base_dir, out_dir = sys.argv[1:5]
nb = json.load(open(src))

for cell in nb["cells"]:
    if cell["cell_type"] != "code":
        continue
    text = "".join(cell["source"])
    text = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("!pip"))
    text = re.sub(r"^BASE_DIR\s*=.*$", f"BASE_DIR = r'{base_dir}'", text, flags=re.M)
    text = re.sub(r"^OUTPUT_DIR\s*=.*$", f"OUTPUT_DIR = r'{out_dir}'", text, flags=re.M)
    cell["source"] = text.splitlines(keepends=True)
    cell["outputs"] = []
    cell["execution_count"] = None
    cell["metadata"] = {}

json.dump(nb, open(dst, "w"), indent=1)
print(f"wrote {dst}")
