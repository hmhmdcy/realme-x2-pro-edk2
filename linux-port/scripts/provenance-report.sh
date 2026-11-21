#!/bin/sh
# Package provenance: how much of the image is stock distribution material,
# and which deviations exist?  Uses the official indexes the image itself
# cached, so the answer is not based on the board's own repository.
set -u
pw() { printf '12345678\n' | sudo -S -p '' "$@"; }

DB=/lib/apk/db/installed
TMP=/tmp/prov
rm -rf "$TMP"; mkdir -p "$TMP/idx"

echo "== unpacking official indexes =="
n=0
for f in /var/cache/apk/APKINDEX.*.tar.gz; do
    d="$TMP/idx/$n"; mkdir -p "$d"
    tar -xzf "$f" -C "$d" APKINDEX 2>/dev/null || continue
    n=$((n + 1))
done
echo "  indexes: $n"

echo "== official name:version inventory =="
awk '/^P:/ {p = substr($0,3)} /^V:/ {print p "\t" substr($0,3)}' \
    "$TMP"/idx/*/APKINDEX | sort -u > "$TMP/official.txt"
echo "  official package entries: $(wc -l < "$TMP/official.txt")"
echo "  official distinct names: $(cut -f1 "$TMP/official.txt" | sort -u | wc -l)"

echo "== installed inventory =="
awk '/^P:/ {p = substr($0,3)} /^V:/ {print p "\t" substr($0,3)}' \
    "$DB" | sort -u > "$TMP/installed.txt"
echo "  installed: $(wc -l < "$TMP/installed.txt")"

echo "== classification =="
# One awk pass with an associative lookup, so the work is O(n) instead of
# 1245 greps over a 30k-line index (which takes many minutes on the phone).
awk -F'\t' '
    NR == FNR { official[$1 "\t" $2] = 1; oname[$1] = 1; next }
    {
        if (!($1 in oname))            { print $0 > "/tmp/prov/private.txt"; pc++ }
        else if (($1 "\t" $2) in official) { ec++ }
        else                            { print $0 > "/tmp/prov/vdiff.txt"; vc++ }
        tt++
    }
    END {
        printf "  identical to an official index entry : %d\n", ec
        printf "  official name, different version     : %d\n", vc
        printf "  not in any official index (board)    : %d\n", pc
        printf "  TOTAL                                : %d\n", tt
    }' "$TMP/official.txt" "$TMP/installed.txt"

echo
echo "== board-only packages (these are the adaptation surface) =="
sort "$TMP/private.txt" | sed 's/^/  /'
echo
echo "== version deviations from official =="
sort "$TMP/vdiff.txt" | sed 's/^/  /'
echo
echo "== whether each board package ships a private *API* or only glue =="
for name in $(cut -f1 "$TMP/private.txt"); do
    bin=$(grep -c '^F:usr/(s?bin|libexec|share/samurai)' "$DB" >/dev/null 2>&1; true)
    printf '  %-34s ' "$name"
    case "$name" in
    device-*)               echo 'deviceinfo/boot glue (standard pmOS format)' ;;
    samurai-systemd)        echo 'systemd units/preset only' ;;
    samurai-platform|samurai-platform-pulse)
                            echo 'ALSA UCM, NM/ModemManager glue, udev rules' ;;
    samurai-desktop)        echo 'session selection + KDE defaults' ;;
    samurai-camera-config|samurai-camera-stack)
                            echo 'libcamera tuning data for board sensors' ;;
    samurai-ssc|samurai-hexagonrpcd|samurai-libssc)
                            echo 'SLPI/sensor daemon (no IIO bridge yet)' ;;
    samurai-radio-tools)    echo 'rmtfs/tqftpserv wrappers' ;;
    samurai-gnss-assist)    echo 'GNSS assist worker over ModemManager' ;;
    usb-signaller*)         echo 'USB gadget role switch (upstream project + board patches)' ;;
    *)                      echo '?' ;;
    esac
done

rm -rf "$TMP"
