# Skeletal Program Enumeration Term Project
# Authors: Rashed Hadi (rmh7), Kavi Godden (kgodden), Manuel Delfin(mda99)

from __future__ import annotations
import argparse
import re
import subprocess
from pathlib import Path

# this file will allow users to run input files on both gcc and tinyc
# and compare the results

#helper to run a fle and capture the stderr
def run_cmd_capture_stderr(cmd):
	try:
		proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
		return proc.returncode, proc.stderr
	except FileNotFoundError as e:
		return 127, f"{e}\n"
	except Exception as e:
		return 1, f"{e}\n"

# helper to run a program and capture stdout (with timeout)
def run_cmd_capture_stdout(cmd, timeout = 2.0):
	try:
		proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
		return proc.returncode, proc.stdout, proc.stderr
	except subprocess.TimeoutExpired as e:
		return 124, e.stdout or "", (e.stderr or "") + "\n[timeout]"
	except FileNotFoundError as e:
		return 127, "", f"{e}\n"
	except Exception as e:
		return 1, "", f"{e}\n"

# extract the line number from the error message in the stderr of gcc and tinyc
_ERR_LINE_RE = re.compile(r":(?P<line>\d+)(?::\d+)?\s*:\s*error:\s*", re.IGNORECASE)
_ERR_LINE_WORD_RE = re.compile(r"line\s+(?P<line>\d+)\b.*error", re.IGNORECASE)
def error_line_number(stderr: str) -> int | None:
	m = _ERR_LINE_RE.search(stderr)
	if m:
		try:
			return int(m.group('line'))
		except Exception:
			pass
	m2 = _ERR_LINE_WORD_RE.search(stderr)
	if m2:
		try:
			return int(m2.group('line'))
		except Exception:
			pass
	return None


# run all c files in a folder
def process_folder(folder, log_file):
	# sort c files
	c_files = sorted(folder.glob("*.c"))
	# track stats for this folder
	local_stats = {
		'processed':0,
		'both_success':0,
		'both_success_same_output':0,
		'both_success_diff_output':0,
		'both_fail_same_line':0,
		'both_fail_diff_line':0,
		'status_mismatch':0,
		'unknown_line':0
	}
	if not c_files:
		return local_stats

	log_file.write(f"===== Starting Test: {folder} =====\n")

	for c_path in c_files:
		c_file = str(c_path)
		base = str(c_path.with_suffix(""))
		
		# run gcc and tinyc on file
		obj_gcc = f"{base}-gcc.o"
		obj_tcc = f"{base}-tcc.o"
		gcc_rc, gcc_err = run_cmd_capture_stderr(["gcc", c_file, "-o", obj_gcc])
		tcc_rc, tcc_err = run_cmd_capture_stderr(["tcc", c_file, "-o", obj_tcc])

		log_file.write(f"- Testing Variant: {c_file}:\n")

		# extract the line number of the first error
		gcc_line = error_line_number(gcc_err)
		tcc_line = error_line_number(tcc_err)

		local_stats['processed'] += 1
		# if both compilers succeed, compare program outputs
		if gcc_rc == 0 and tcc_rc == 0:
			local_stats['both_success'] += 1
			log_file.write("   result: both compilers succeeded\n")
			_, gcc_out, _= run_cmd_capture_stdout([obj_gcc])
			_, tcc_out, _= run_cmd_capture_stdout([obj_tcc])
			if gcc_out == tcc_out:
				local_stats['both_success_same_output'] += 1
				log_file.write("   output: identical\n")
			else:
				local_stats['both_success_diff_output'] += 1
				log_file.write("   output: differ\n")
				log_file.write("   --- gcc stdout ---\n")
				if gcc_out:
					for line in gcc_out.splitlines():
						log_file.write(f"   {line}\n")
				else:
					log_file.write("   <empty>\n")
				log_file.write("   --- tcc stdout ---\n")
				if tcc_out:
					for line in tcc_out.splitlines():
						log_file.write(f"   {line}\n")
				else:
					log_file.write("   <empty>\n")
		else:
			if (gcc_rc != 0) and (tcc_rc != 0):
				# if both compilers failed, we check different cases
				if gcc_line is not None and tcc_line is not None:
					# case 1: same line number
					if gcc_line == tcc_line:
						local_stats['both_fail_same_line'] += 1
						log_file.write(f"   result: both failed on line {gcc_line}, no differences\n")
					# case 2: different line number
					else:
						local_stats['both_fail_diff_line'] += 1
						log_file.write(f"   gcc failed on line {gcc_line}\n")
						log_file.write(f"   tcc failed on line {tcc_line}\n")
						log_file.write("   result: both failed on different lines, differences found\n")
						# print error lines
						log_file.write("   --- gcc errror ---\n")
						log_file.write(f"   {gcc_err}\n")
						log_file.write("   --- tcc errror ---\n")
						log_file.write(f"   tcc error: {tcc_err}\n")
						log_file.write("   ------------------\n")
				else:
					# here if we couldnt parse line numbers
					local_stats['unknown_line'] += 1
					log_file.write("   result: both failed; could not extract line number from one or both compilers\n")
					log_file.write(f"   gcc error: {gcc_err}\n")
					log_file.write(f"   tcc error: {tcc_err}\n")
			else:
				# this case means one compiler succeeded and one failed
				local_stats['status_mismatch'] += 1
				log_file.write("   result: status mismatch (one failed, one succeeded)\n")
				log_file.write(f"   gcc error: {gcc_err}\n")
				log_file.write(f"   tcc error: {tcc_err}\n")
	return local_stats


def main():
	parser = argparse.ArgumentParser(description="Test variants in output directory using gcc and tcc")
	parser.add_argument("input_dir", help="Path to 'output' directory containing per-test subfolders with .c variants")
	parser.add_argument(
		"--log",
		dest="log_path",
		help="Path to write combined log (default: <output_dir>/<name>-diff-log.txt)",
		default=None,
	)
	args = parser.parse_args()

	# check if dir exitsts
	root = Path(args.input_dir)
	if not root.exists():
		raise FileNotFoundError(f"Output directory does not exist: {args.input_dir}")

	default_log = root / f"{root.name}-diff-log.txt"
	log_path = Path(args.log_path) if args.log_path else default_log

	with open(log_path, "w", encoding="utf-8") as log_file:
		# file intro
		log_file.write("Skeletal Program Enumeration for TinyC Stress Testing\n")
		log_file.write("Authors: Rashed Hadi (rmh7), Kavi Godden (kgodden), Manuel Delfin(mda99)\n")
		log_file.write(f"Input Directory: {root}\n")

		# we will track if the errors in tinyc and gcc are the same
		# by comparing the line numbers of the first error reported in stderr
		summary_stats = {
			'processed':0,
			'both_success':0,
			'both_success_same_output':0,
			'both_success_diff_output':0,
			'both_fail_same_line':0,
			'both_fail_diff_line':0,
			'status_mismatch':0,
			'unknown_line':0
		}

		def accumulate_stats(dst, src):
			for k in dst:
				dst[k] += src.get(k, 0)

		accumulate_stats(summary_stats, process_folder(root, log_file))

		# Then process each immediate subfolder
		for entry in sorted(root.iterdir()):
			if entry.is_dir():
				accumulate_stats(summary_stats, process_folder(entry, log_file))

		# write summary
		log_file.write("\n===== Summary =====\n")
		log_file.write(f"Total tests processed: {summary_stats['processed']}\n")
		log_file.write(f"Total tests both compilers succeeded: {summary_stats['both_success']}\n")
		log_file.write(f"  - Same stdout: {summary_stats['both_success_same_output']}\n")
		log_file.write(f"  - Different stdout: {summary_stats['both_success_diff_output']}\n")
		log_file.write(f"Total tests both failed on same line: {summary_stats['both_fail_same_line']}\n")
		log_file.write(f"Total tests both failed on different lines: {summary_stats['both_fail_diff_line']}\n")
		log_file.write(f"Total tests with status mismatch (one failed): {summary_stats['status_mismatch']}\n")
		log_file.write(f"Total Tests with unknown line numbers: {summary_stats['unknown_line']}\n")

	print(f"Wrote diff summary to: {log_path}")


if __name__ == "__main__":
	main()

