# Skeletal Program Enumeration Term Project
# Authors: Rashed Hadi (rmh7), Kavi Godden (kgodden), Manuel Delfin(mda99)

from __future__ import annotations
import argparse
import os
import shutil
from pathlib import Path
from .parsing import parse_c_program
from .enumeration import enumerate_programs_algo1
from .generator import materialize_variants

# main file controling the whole skeletal program enumeration process

def enumerate_file(source_path: str, dest_dir: str) -> list[str]:
	print(f" - Starting analysis of: {source_path} -")
	with open(source_path, "r", encoding="utf-8") as f:
		source_code = f.read()

	parse_result = parse_c_program(source_code)
	program_vectors = enumerate_programs_algo1(parse_result)

	base_name = os.path.splitext(os.path.basename(source_path))[0]
	# if no variants were created, write the original source as __0000.c
	if not program_vectors:
		os.makedirs(dest_dir, exist_ok=True)
		file_name = f"{base_name}__0000.c"
		file_path = os.path.join(dest_dir, file_name)
		with open(file_path, "w", encoding="utf-8") as out_f:
			out_f.write(source_code)
		return [file_path]

	written_paths = materialize_variants(
		source_code=source_code,
		program_vectors=program_vectors,
		dest_dir=dest_dir,
		base_name=base_name,
	)
	return written_paths


def get_c_files(input_dir: str) -> list[Path]:
	root = Path(input_dir)
	if not root.exists():
		raise FileNotFoundError(f"ERROR: Input directory does not exist: {input_dir}")
	return sorted(p for p in root.glob("*.c") if p.is_file())


def main():
	parser = argparse.ArgumentParser(description="Skeeletal Program Enumeration of C Programs in Input Directory",)
	parser.add_argument("input_dir", help="Directory containing input .c files to enumerate")
	parser.add_argument("output_dir", help="Directory to write variant files into")
	args = parser.parse_args()

	# clear output directory before starting
	if os.path.exists(args.output_dir):
		shutil.rmtree(args.output_dir)

    # make output directory if it doesn't exist
	os.makedirs(args.output_dir, exist_ok=True)
	c_files = get_c_files(args.input_dir)
	if not c_files:
		print(f"ERROR: No .c files found in {args.input_dir}")
		return

	print(f"---- Found {len(c_files)} C files to process ----")

	for cfile in c_files:
		file_name = cfile.stem
		file_out_dir = os.path.join(args.output_dir, file_name)
		os.makedirs(file_out_dir, exist_ok=True)
		try:
			written = enumerate_file(str(cfile), file_out_dir)
			print(f"     Generated {len(written)} variant files in {file_out_dir}")
		except Exception as exc:
			print(f"     Error processing {cfile.name}: {exc}")


if __name__ == "__main__":
	main()
