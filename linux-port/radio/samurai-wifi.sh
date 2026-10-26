#!/bin/sh
# Same-handset firmware and NV sources are read only; writes stay in RAM.
set -eu
umask 077
base=/run/samurai-wifi
firmware=qcom/sm8150/realme/samurai
resolve()
{
    matches=0
    found=
    for attrs in /sys/class/block/sd*/uevent; do
        if grep -qx "PARTNAME=$1" "$attrs"; then
            node=${attrs%/uevent}; node=${node##*/}
            test -b "/dev/$node" || return 1
            [ "$(cat "/sys/class/block/$node/size")" = "$2" ] || return 1
            parent=$(readlink -f "/sys/class/block/$node/..")
            [ "$(cat "$parent/device/model")" = 'KLUDG4UHDB-B2D1 ' ] || return 1
            found=/dev/$node
            matches=$((matches+1))
        fi
    done
    [ "$matches" -eq 1 ] || return 1
    printf '%s\n' "$found"
}
all_sources_ready()
{
    for spec in modem:524288 modemst1:4096 modemst2:4096 fsg:4096 fsc:256 oppostanvbk:20480 oppodycnvbk:20480; do
        resolve "${spec%%:*}" "${spec#*:}" > /dev/null 2>&1 || return 1
    done
}
prepare()
{
    mpss=$(/usr/sbin/samurai-modem-remoteproc)
    tr '\0' '\n' < /proc/device-tree/compatible | grep -qx realme,samurai
    [ "$(cat $mpss/state)" = offline ]
    [ "$(cat $mpss/firmware)" = "$firmware/modem.mdt" ]
    test ! -e "$base/nv"
    test ! -e "$base/firmware"
    modem=$(resolve modem 524288)
    mkdir -p "$base/stock-modem" "$base/firmware/$firmware" "$base/nv"
    mount -t vfat -o ro,nosuid,nodev,noexec "$modem" "$base/stock-modem"
    # Each manifest entry is a fixed basename generated from the verified
    # same-handset archive. No path from a remote request is accepted here.
    while read -r hash name; do
        case "$name" in modem.b[0-9][0-9]|modem.mdt|modemr.jsn|modemuw.jsn|wlanmdsp.mbn) ;;
            *) exit 1;; esac
        test -f "$base/stock-modem/image/$name"
        test ! -L "$base/stock-modem/image/$name"
        cp "$base/stock-modem/image/$name" "$base/firmware/$firmware/$name"
    done < /etc/samurai-wifi/modem-sha256.txt
    (cd "$base/firmware/$firmware" && sha256sum -c /etc/samurai-wifi/modem-sha256.txt) > "$base/firmware-check.txt"
    mkdir -m 0700 "$base/mcfg-state"
    /usr/sbin/samurai-modem-configs "$base/stock-modem/image" "$base/firmware/$firmware" "$base/mcfg-state/source-manifest-private.json" > "$base/mcfg-prepare.log"
    umount "$base/stock-modem"
    cp -a /lib/firmware/ath10k "$base/firmware/"
    : > "$base/nv-source-hashes.txt"
    for spec in modemst1:4096:modem_fs1 modemst2:4096:modem_fs2 fsg:4096:modem_fsg fsc:256:modem_fsc oppostanvbk:20480:oem_stanvbk oppodycnvbk:20480:oem_dycnvbk; do
        label=${spec%%:*}; rest=${spec#*:}; sectors=${rest%%:*}; name=${rest#*:}
        source=$(resolve "$label" "$sectors")
        before=$(sha256sum "$source" | cut -d ' ' -f1)
        dd "if=$source" "of=$base/nv/$name" bs=512 > "$base/nv-$name-copy.log" 2>&1
        [ "$(wc -c < "$base/nv/$name")" -eq "$((sectors*512))" ]
        copy=$(sha256sum "$base/nv/$name" | cut -d ' ' -f1)
        after=$(sha256sum "$source" | cut -d ' ' -f1)
        [ "$before" = "$copy" ] && [ "$before" = "$after" ]
        printf '%s  %s\n' "$before" "$source" >> "$base/nv-source-hashes.txt"
    done
    (cd "$base/nv" && sha256sum *) > "$base/nv-snapshot-sha256.txt"
    echo "$base/firmware" > /sys/module/firmware_class/parameters/path
    echo PREPARE_OK
}
start()
{
    test ! -e "$base/ready"
    sources_ready=0
    for attempt in $(seq 1 60); do
        if mpss=$(/usr/sbin/samurai-modem-remoteproc) && all_sources_ready; then
            sources_ready=1
            break
        fi
        echo "WIFI_WAIT_SOURCES attempt=$attempt uptime=$(cut -d ' ' -f1 /proc/uptime)"
        sleep 1
    done
    [ "$sources_ready" = 1 ] || { echo WIFI_SOURCE_WAIT_TIMEOUT >&2; return 1; }
    prepare
    # Firmware work files are volatile and bounded independently of NV COW.
    mkdir -m 0700 "$base/tftp-rw"
    mount -t tmpfs -o size=32m,mode=0700,nosuid,nodev,noexec tmpfs "$base/tftp-rw"
    SAMURAI_TFTP_RW_ROOT="$base/tftp-rw" SAMURAI_TFTP_FIRMWARE_ROOT="$base/firmware/$firmware" /usr/sbin/samurai-tqftpserv -d > "$base/tftp.log" 2>&1 &
    echo $! > "$base/tftp.pid"
    /usr/sbin/samurai-rmtfs-cow > "$base/rmtfs.log" 2>&1 &
    echo $! > "$base/rmtfs.pid"
    sleep 1
    kill -0 "$(cat "$base/tftp.pid")" "$(cat "$base/rmtfs.pid")"
    grep -q 'RMTFS RAM COW ready' "$base/rmtfs.log"
    /usr/sbin/qrtr-lookup > "$base/qrtr-before.txt"
    grep -qE '^ *14 ' "$base/qrtr-before.txt"
    grep -qE '^ *4096 ' "$base/qrtr-before.txt"
    echo disabled > $mpss/recovery
    echo start > $mpss/state
    for attempt in $(seq 1 60); do
        test -e /sys/class/net/wlan0 && break
        sleep 1
    done
    test -e /sys/class/net/wlan0
    /usr/sbin/samurai-radio-address wlan
    ip link set wlan0 up
    if [ "${SAMURAI_WIFI_MANAGED:-0}" != 1 ]; then
    cp /etc/samurai-wifi/wpa-empty.conf "$base/wpa.conf"
    nohup /usr/sbin/wpa_supplicant -Dnl80211 -iwlan0 -c"$base/wpa.conf" > "$base/wpa.log" 2>&1 < /dev/null &
    echo $! > "$base/wpa.pid"
    sleep 1
    /usr/sbin/wpa_cli -p"$base/wpa-control" -iwlan0 ping | grep -qx PONG
    fi
    sleep 45
    [ "$(cat $mpss/state)" = running ]
    kill -0 "$(cat "$base/tftp.pid")" "$(cat "$base/rmtfs.pid")"
    if [ "${SAMURAI_WIFI_MANAGED:-0}" != 1 ]; then
        kill -0 "$(cat "$base/wpa.pid")"
    fi
    sha256sum -c "$base/nv-source-hashes.txt" > "$base/nv-after-start.txt"
    touch "$base/ready"
    echo WIFI_READY
}
mkdir -p "$base"
case "${1:-}" in
    prepare) prepare ;;
    start) start ;;
    *) echo 'Use prepare or start' >&2; exit 2 ;;
esac
