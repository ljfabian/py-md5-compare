#!/bin/bash

echo 'initiating Mamba env...'
. ~/.initMamba.sh
mamba activate standard

dir1=$1
dir2=$2

threads=$(nproc)
echo "threads: ${threads}"

echo "comparing:"
echo "${dir1}"
echo "${dir2}"

# build one --ignore per remaining argument
ignore_args=()
for f in "$@"; do
    ignore_args+=(--ignore "$f")
done

python md5_compare_optimised.py \
    -d1 "$dir1" \
    -d2 "$dir2" \
    -t "${threads}" \
    "${ignore_args[@]}"
