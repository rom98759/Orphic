import os
import re
import argparse

# Regular expressions
# This regex detects a typical function definition (note: simplified)
FUNC_DEF_REGEX = re.compile(
	r"^\s*(?!if\s*\(|while\s*\(|for\s*\(|switch\s*\(|return\s*\(|sizeof\s*\(|case\s*\(|default\s*\(|else\s+if\s*\()"
	r"(?:[a-zA-Z_][a-zA-Z0-9_]*\s+)+\**([a-zA-Z_][a-zA-Z0-9_]*)\s*\(",
	re.MULTILINE
)

# This regex detects a function call
FUNC_CALL_REGEX = re.compile(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*\(")

def remove_comments(text):
	"""
	Removes C-style comments (both block and line comments) from the given text.
	"""
	# Remove multi-line comments (/* ... */)
	text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
	# Remove single-line comments (// ...)
	text = re.sub(r'//.*', '', text)
	return text

def find_function_definitions_in_file(filepath):
	"""
	Finds function definitions in a file and returns a list of tuples:
	(function_name, line_number, filepath)
	"""
	definitions = []
	try:
		with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
			content = f.read()
	except Exception as e:
		print(f"Error reading {filepath}: {e}")
		return definitions

	# Remove comments to avoid false matches.
	content = remove_comments(content)

	# Use finditer to capture the function name and its position.
	for match in FUNC_DEF_REGEX.finditer(content):
		function_name = match.group(1)
		# Calculate the line number by counting the newlines before the match.
		line_number = content[:match.start()].count("\n") + 1
		definitions.append((function_name, line_number, filepath))
	return definitions

def find_function_calls_in_file(filepath):
	"""
	Finds function calls in a file and returns a set of function names.
	It removes comments and function definitions to avoid counting signatures as calls.
	"""
	try:
		with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
			content = f.read()
	except Exception as e:
		print(f"Error reading {filepath}: {e}")
		return set()

	# Remove comments first.
	content = remove_comments(content)
	# Remove function definitions so that signatures are not counted as calls.
	content_without_defs = FUNC_DEF_REGEX.sub("", content)
	return set(FUNC_CALL_REGEX.findall(content_without_defs))

def scan_path(path):
	"""
	Scans a single file or directory.

	If path is a directory, it recursively scans for .c and .h files.
	If path is a file (and ends with .c or .h), it scans that file.

	Returns:
		definitions: a dictionary mapping function names to a list of tuples (filepath, line_number)
		calls: a set of function names that are called.
	"""
	definitions = {}
	calls = set()

	if os.path.isdir(path):
		# Recursively traverse the directory
		for root, _, files in os.walk(path):
			for file in files:
				if file.endswith(".c") or file.endswith(".h"):
					filepath = os.path.join(root, file)
					file_defs = find_function_definitions_in_file(filepath)
					for func_name, line_number, fpath in file_defs:
						definitions.setdefault(func_name, []).append((fpath, line_number))
					file_calls = find_function_calls_in_file(filepath)
					calls.update(file_calls)
	elif os.path.isfile(path) and (path.endswith(".c") or path.endswith(".h")):
		file_defs = find_function_definitions_in_file(path)
		for func_name, line_number, fpath in file_defs:
			definitions.setdefault(func_name, []).append((fpath, line_number))
		file_calls = find_function_calls_in_file(path)
		calls.update(file_calls)
	else:
		print(f"Skipping '{path}': Not a .c or .h file or directory.")

	return definitions, calls

def scan_inputs(paths):
	"""
	Scans multiple paths (files or directories).

	Returns:
		all_definitions: a dictionary mapping function names to a list of tuples (filepath, line_number)
		all_calls: a set of function names that are called.
	"""
	all_definitions = {}
	all_calls = set()

	for path in paths:
		defs, calls = scan_path(path)
		for func_name, locations in defs.items():
			all_definitions.setdefault(func_name, []).extend(locations)
		all_calls.update(calls)
	return all_definitions, all_calls

def print_header(title, width=80):
	"""
	Prints a header with a given title centered within a line of '=' characters.
	"""
	print("\033[96m" + "=" * width + "\033[0m")
	print("\033[96m" + title.center(width) + "\033[0m")
	print("\033[96m" + "=" * width + "\033[0m")

def print_function_location(func_name, locations):
	"""
	Prints the function name and its locations in a formatted manner with colors.
	Files with .c extensions are shown in blue, while .h files are shown in yellow.
	"""
	for path, line in locations:
		# Colorize the file path based on extension
		if path.endswith(".c"):
			file_color = "\033[94m"  # Blue for .c files
		elif path.endswith(".h"):
			file_color = "\033[93m"  # Yellow for .h files
		else:
			file_color = "\033[0m"  # No color for other files

		# Print function location with colorized file path
		print(f"\033[92m{func_name:25}\033[0m | {file_color}{path:30}\033[0m line: \033[91m{line}\033[0m")

def main():
	parser = argparse.ArgumentParser(
		description="Scan one or more directories or files for C function definitions and calls."
	)
	parser.add_argument(
		"sources",
		nargs="+",
		help="One or more directories or .c/.h files to scan."
	)
	args = parser.parse_args()

	# If no sources are provided (shouldn't happen with nargs="+"), exit.
	if not args.sources:
		print("No input paths provided. Exiting.")
		return

	definitions, calls = scan_inputs(args.sources)

	# Display defined functions in a clean table format.
	print_header("Defined Functions")
	if definitions:
		print(f"{'Function':25} | Location")
		print("\033[96m" + "-" * 80 + "\033[0m")
		for func_name, locations in sorted(definitions.items()):
			print_function_location(func_name, locations)
	else:
		print("No function definitions found.")

	# Display all called functions.
	print("\n")
	print_header("Called Functions")
	if calls:
		for func in sorted(calls):
			print("\033[92m" + func + "\033[0m")
	else:
		print("No function calls found.")

	# Identify unused functions (excluding 'main' since it's called by the runtime)
	unused = {}
	for func_name, locations in definitions.items():
		if func_name not in calls and func_name != "main":
			unused[func_name] = locations

	print("\n")
	print_header("Unused Functions")
	if unused:
		print(f"{'Function':25} | Location")
		print("\033[96m" + "-" * 80 + "\033[0m")
		for func_name, locations in sorted(unused.items()):
			print_function_location(func_name, locations)
	else:
		print("All functions are used!")
	print("\n")

if __name__ == "__main__":
	main()
