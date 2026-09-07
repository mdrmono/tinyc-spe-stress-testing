# Skeletal Program Enumeration Term Project
# Authors: Rashed Hadi (rmh7), Kavi Godden (kgodden), Manuel Delfin(mda99)

from __future__ import annotations
import os
from .spe_types import ParseResult, Hole

# file for building the variant programs and writing them to files

def build_replacement_map(program_vector):
    replacements = []

    for _, func_payload in program_vector["by_function"].items():
        holes = func_payload.get("holes", [])
        assignments = func_payload.get("assignments", [])

        if len(holes) != len(assignments):
            continue

        for hole_info, assign_info in zip(holes, assignments):
            start = int(hole_info["start"])
            end = int(hole_info["end"])
            var_name = str(assign_info["var_name"])
            replacements.append((start, end, var_name))

    return replacements


def apply_replacements(source_code, replacements):
    if len(replacements) == 0:
        return source_code

    replacements_sorted = sorted(replacements, key=lambda x: x[0], reverse=True)

    updated = source_code
    for start, end, text in replacements_sorted:
        if start < 0 or end > len(updated) or start > end:
            continue
        updated = updated[:start] + text + updated[end:]

    return updated


def materialize_variants(
    source_code,
    program_vectors,
    dest_dir,
    base_name,
):
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir, exist_ok=True)

    written_paths = []

    for idx, program_vector in enumerate(program_vectors):
        replacements = build_replacement_map(program_vector)
        enumerated_code = apply_replacements(source_code, replacements)

        file_name = f"{base_name}__{idx:04d}.c"
        file_path = os.path.join(dest_dir, file_name)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(enumerated_code)
        written_paths.append(file_path)

    return written_paths


__all__ = ["materialize_variants"]