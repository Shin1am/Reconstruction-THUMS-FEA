"""
Convert a registered .vtu (with 'node_id' point data, produced by one of the
CPD_TPS_* pipelines) back into an LS-DYNA .k file. Only the *NODE block
coordinates of the ORIGINAL .k are patched -- every other card (elements,
parts, materials) stays byte-identical.

Usage:
    python vtu_to_k.py <original.k> <registered.vtu> <output.k>
"""
import sys
import pyvista as pv


def parse_node_block(k_path):
    with open(k_path, 'r', errors='replace') as fh:
        raw_lines = fh.readlines()
    node_line_indices = {}
    in_node_block = False
    for line_idx, line in enumerate(raw_lines):
        stripped = line.strip()
        if stripped.startswith('*'):
            in_node_block = stripped.upper().startswith('*NODE')
            continue
        if stripped.startswith('$') or stripped == '':
            continue
        if in_node_block:
            try:
                nid = int(line[0:8])
                node_line_indices[nid] = line_idx
            except (ValueError, IndexError):
                continue
    return raw_lines, node_line_indices


def write_k(raw_lines, node_line_indices, node_ids, coords, output_path):
    new_lines = list(raw_lines)
    missing = 0
    for nid, (x, y, z) in zip(node_ids, coords):
        nid = int(nid)
        line_idx = node_line_indices.get(nid)
        if line_idx is None:
            missing += 1
            continue
        original_line = raw_lines[line_idx]
        suffix = original_line[56:].rstrip('\n') if len(original_line) > 56 else ''
        # width 17 (not 16) so a negative value's 16-char content never runs
        # into the neighboring field with no delimiter
        new_lines[line_idx] = f'{nid:>8d}{x:>17.9E}{y:>17.9E}{z:>17.9E}{suffix}\n'
    with open(output_path, 'w') as fh:
        fh.writelines(new_lines)
    if missing:
        print(f'WARNING: {missing} node IDs from the .vtu were not found in the .k -- skipped')
    print(f'Wrote -> {output_path}')


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    orig_k, registered_vtu, out_k = sys.argv[1:4]

    raw_lines, node_line_indices = parse_node_block(orig_k)
    print(f'Original .k: {len(node_line_indices):,} nodes in *NODE block')

    mesh = pv.read(registered_vtu)
    node_ids = mesh.point_data['node_id']
    coords = mesh.points
    print(f'Registered .vtu: {len(node_ids):,} points')

    write_k(raw_lines, node_line_indices, node_ids, coords, out_k)


if __name__ == '__main__':
    main()
