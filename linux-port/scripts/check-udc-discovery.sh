#!/bin/sh
# Offline tests for the UDC discovery used by samurai-usb.
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT

failures=0

run_discover() {
    target=$1
    udc_dir=$2
    forced_udc=$3
    if [ -n "$forced_udc" ]; then
        SAMURAI_UDC_DIR="$udc_dir" SAMURAI_UDC="$forced_udc" \
            sh "$target" discover
    else
        SAMURAI_UDC_DIR="$udc_dir" sh "$target" discover
    fi
}

check_case() {
    target=$1
    name=$2
    expected_status=$3
    expected_output=$4
    udc_dir=$5
    forced_udc=${6:-}
    out=$workdir/out
    err=$workdir/err
    set +e
    run_discover "$target" "$udc_dir" "$forced_udc" >"$out" 2>"$err"
    status=$?
    set -e
    actual=$(cat "$out")
    if [ "$status" -ne "$expected_status" ] ||
       [ "$actual" != "$expected_output" ]; then
        echo "FAIL $target: $name (status=$status output='$actual')" >&2
        cat "$err" >&2
        failures=$((failures + 1))
    else
        echo "PASS $target: $name"
    fi
}

case_dir() {
    dir=$workdir/$1
    mkdir -p "$dir"
    shift
    for udc in "$@"; do
        mkdir -p "$dir/$udc"
    done
    printf '%s\n' "$dir"
}

single_preferred=$(case_dir single_preferred a600000.usb)
single_other=$(case_dir single_other dwc3.0)
multiple=$(case_dir multiple dwc3.0 dwc3.1)
preferred_multiple=$(case_dir preferred_multiple a600000.usb dwc3.0)
bogus=$(case_dir bogus a600000.usb)
empty=$(case_dir empty)

for target in \
    "$script_dir/../packages/samurai-platform/usr_sbin_samurai-usb" \
    "$script_dir/samurai-usb.sh"
do
    check_case "$target" preferred-single 0 a600000.usb "$single_preferred"
    check_case "$target" single-fallback 0 dwc3.0 "$single_other"
    check_case "$target" preferred-multiple 0 a600000.usb "$preferred_multiple"
    check_case "$target" multiple-ambiguous 1 '' "$multiple"
    check_case "$target" explicit-override 0 dwc3.1 "$multiple" dwc3.1
    check_case "$target" explicit-missing 1 '' "$bogus" missing.udc
    check_case "$target" no-udc 1 '' "$empty"
done

if [ "$failures" -ne 0 ]; then
    echo "$failures discovery case(s) failed" >&2
    exit 1
fi

echo "UDC discovery: PASS"
