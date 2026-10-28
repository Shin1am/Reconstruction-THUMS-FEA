"""
Skull / Brain / Skull+Brain(+meninges) Extractor
=================================================
Wraps extract_head.py's parser and writer to produce three
self-contained .k files from a single input:

    1. <base>_skull_brain_meninges.k  -- skull + brain + meninges/CSF
    2. <base>_skull_only.k            -- skull only
    3. <base>_brain_only.k            -- brain parenchyma only

Usage:
    python extract_skull_brain_parts.py Head_V6.k
    python extract_skull_brain_parts.py Head_V6.k --outdir /path/to/dir
"""

import os
import sys

from extract_head import (
    parse_full_k,
    extract_head,
    SKULL_ALL,
    BRAIN,
    MENINGES_CSF,
)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_k = sys.argv[1]
    outdir_arg = next((sys.argv[i + 1] for i, a in enumerate(sys.argv)
                        if a == "--outdir" and i + 1 < len(sys.argv)), None)

    base_dir = outdir_arg if outdir_arg else os.path.dirname(os.path.abspath(input_k))
    base_name = os.path.splitext(os.path.basename(input_k))[0]

    print(f"\nParsing: {input_k}")
    data = parse_full_k(input_k)
    print(f"Loaded : {len(data['nodes'])} nodes, "
          f"{len(data['elems_solid'])} solids, "
          f"{len(data['elems_shell'])} shells across "
          f"{len(data['parts'])} parts\n")

    targets = [
        ("skull_brain_meninges", set(SKULL_ALL) | set(BRAIN) | set(MENINGES_CSF)),
        ("skull_only",           set(SKULL_ALL)),
        ("brain_only",           set(BRAIN)),
    ]

    for label, pids in targets:
        out_path = os.path.join(base_dir, f"{base_name}_{label}.k")
        print(f"=== {label}  ({len(pids)} PIDs) ===")
        extract_head(data, pids, out_path)
        print()

    print("Done. Next step: run k_mesh_qa.py on each output to verify quality + node count.")


if __name__ == "__main__":
    main()
