"""
Convert a Slicer3D Markups Fiducial export (.fcsv) to a plain Nx3 .npy array
in RAS (the convention used by the .k/.vtu mesh coordinates throughout this
project). Slicer's own header line declares which coordinate system the file
was written in -- this script reads that line and flips sign on X/Y if it
says LPS, rather than assuming.

Usage:
    python fcsv_to_npy.py template_landmarks.fcsv template_landmarks.npy
    python fcsv_to_npy.py subject_landmarks.fcsv  subject_landmarks.npy
"""
import sys
import numpy as np


def load_fcsv(path):
    coord_system = None
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith('#'):
                if 'CoordinateSystem' in line:
                    coord_system = line.split('=')[-1].strip().upper()
                continue
            vals = line.split(',')
            x, y, z = float(vals[1]), float(vals[2]), float(vals[3])
            rows.append((x, y, z))

    pts = np.array(rows, dtype=np.float64)
    if coord_system is None:
        print("  WARNING: no CoordinateSystem header found -- assuming RAS. "
              "Verify against a known point if positions look off.")
        coord_system = 'RAS'

    print(f'  Detected coordinate system: {coord_system}')
    if coord_system == 'LPS':
        pts[:, 0] *= -1
        pts[:, 1] *= -1
        print('  Converted LPS -> RAS (flipped X, Y sign)')
    elif coord_system != 'RAS':
        print(f"  WARNING: unrecognized coordinate system '{coord_system}', left as-is")

    return pts


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    in_path, out_path = sys.argv[1], sys.argv[2]
    pts = load_fcsv(in_path)
    print(f'  Loaded {len(pts)} points from {in_path}')
    for i, p in enumerate(pts):
        print(f'    [{i}] {p.round(2)}')
    np.save(out_path, pts)
    print(f'Wrote -> {out_path}')


if __name__ == '__main__':
    main()
