import argparse
import hashlib
import os
import sys
import logging
import fnmatch
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


# init commmand line arguements
def parse_args():
    parser = argparse.ArgumentParser(description="Compare files and folders in 2 directories via md5sum")
    parser.add_argument("-d1", "--dir1", required=True, help="Path to the first directory")
    parser.add_argument("-d2", "--dir2", required=True, help="Path to the second directory")
    parser.add_argument("-v", "--verbose", action='store_true', help="Print match status for every file")
    parser.add_argument("-t", "--threads", type=int, default=4, help="Number of threads to use, defaults to 4")
    parser.add_argument("-f", "--fast", action='store_true', help="Skip files with identical size and mtime (faster but less strict)")
    parser.add_argument("-i", "--ignore", action="append", default=[], help="Files to be ignored during the comparison. Can be used for metadata or such files on one site. Can be used multiple times.")
    return parser.parse_args()


# init the logging
def setup_logging(verbose):
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )


# fetch md5sum for a file
def compute_md5(filepath, buffer_size=8192):
    try:
        hasher = hashlib.md5()
        with open(filepath, 'rb') as f:
            while chunk := f.read(buffer_size):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        logging.error(f"Failed to read {filepath}: {e}")
        return None


# fetch all files from a directory
def get_all_files(directory, excluded_dirs=None, ignore_files=None):
    default_ignore_files = {'.DS_Store', 'backup.acl'}
    default_ignore_folders = {'.snakemake', '.biomake'}

    excluded_dirs = default_ignore_folders | set(excluded_dirs or [])
    ignore_patterns = default_ignore_files | set(ignore_files or [])

    def is_ignored(rel_path):
        name = rel_path.name
        full = rel_path.as_posix()
        return any(
            fnmatch.fnmatchcase(name, pat) or fnmatch.fnmatchcase(full, pat)
            for pat in ignore_patterns
        )

    result = []
    
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in excluded_dirs]
        for file in files:
            rel_path = (Path(root) / file).relative_to(directory)
            if any(part in excluded_dirs for part in rel_path.parts):
                continue
            # if file in ignore_files or rel_path.as_posix() in ignore_files:
            if is_ignored(rel_path):
                continue
            result.append(rel_path)
    return result


# function to compare the files 
def compare_files(rel_path, dir1, dir2, fast=False):
    file1 = dir1 / rel_path
    file2 = dir2 / rel_path

    try:
        stat1 = file1.stat()
        stat2 = file2.stat()

        if fast and stat1.st_size == stat2.st_size and int(stat1.st_mtime) == int(stat2.st_mtime):
            return rel_path, True, "SKIPPED", "SKIPPED"

    except Exception as e:
        logging.error(f"Failed to stat files: {rel_path} - {e}")
        return rel_path, False, None, None

    md5_1 = compute_md5(file1)
    md5_2 = compute_md5(file2)

    if md5_1 is None or md5_2 is None:
        return rel_path, False, md5_1, md5_2

    return rel_path, md5_1 == md5_2, md5_1, md5_2

def main():
    # fetch command line arguements
    args = parse_args()
    setup_logging(args.verbose)

    # check directories exist
    dir1 = Path(args.dir1).resolve()
    dir2 = Path(args.dir2).resolve()

    # fetch files from each directory
    files1 = get_all_files(dir1, ignore_files=args.ignore)
    files2 = get_all_files(dir2, ignore_files=args.ignore)

    # check if the file names match between the two directories
    set1, set2 = set(files1), set(files2)

    # if no match, log the error
    if set1 != set2:
        logging.warning("Mismatch in file names:")
        logging.warning("Only in dir1: %s", sorted(set1 - set2))
        logging.warning("Only in dir2: %s", sorted(set2 - set1))
        sys.exit(1)

    logging.info("Both directories contain the same filenames.\n")

    # otherwise, all file names match between directories 
    all_match = True
    
    # use specified threads to help parrallelise the workload
    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = {
            executor.submit(compare_files, rel_path, dir1, dir2, args.fast): rel_path
            for rel_path in files1
        }
        for future in as_completed(futures):
            rel_path, match, md5a, md5b = future.result()
            if match:
                if args.verbose:
                    if md5a == "SKIPPED":
                        logging.debug(f"[SKIPPED] {rel_path}")
                    else:
                        logging.debug(f"[MATCH] {rel_path}")
            else:
                all_match = False
                logging.error(f"[MISMATCH] {rel_path}\n  Dir1: {md5a}\n  Dir2: {md5b}")

    # print success or failures of matching md5sums
    if all_match:
        logging.info("✅ All files matched successfully.")
    else:
        logging.info("❌ Mismatches found.")

if __name__ == '__main__':
    main()

