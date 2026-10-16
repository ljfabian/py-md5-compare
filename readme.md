# Md5 compare
Code to compare md5sums of files which are present in two separate directories. This is used to compare freeze/out/data/* to the project data folders, checking the rsync worked correctly. 

Usage:
```bash
python md5sum_compared.py \
    -d1 <directory/1/file/path> \
    -d2 <directory/2/file/path> \
    -i <relevant/path/to/ignore1> \
    -i <relevant/path/to/ignore2>
``` 

Optional arguements:
- `--verbose` or `-v`: Print match status for every file
- `--threads` or `-t`: Number of threads to use, defaults to 4
- `--fast` or `-f`: Skip md5 check on files with identitical sizes and mtime (faster, less strict)
- `--ignore` or `-i`: Files to be ignored during the comparison. Can be used for metadata or such files on one site. Can be used multiple times. 

Author: Laurie Fabian 16/10/2026
