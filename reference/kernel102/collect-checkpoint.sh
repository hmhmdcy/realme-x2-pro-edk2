#!/bin/sh
set -eu
umask 077
[ "$#" = 1 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$1" ]
uname -a | grep -q '#101 SMP PREEMPT'
mpss=$(/usr/sbin/samurai-modem-remoteproc)
[ "$(cat "$mpss/state")" = running ]
adsp=$(cat /tmp/k102-audio-runtime-retry1/adsp-path.txt)
[ "$(cat "$adsp/state")" = running ]
grep -qx 0 /run/samurai-wifi/boot-finished
grep -qx AUTO_BOOT_5G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS /tmp/k102-auto-network-completion/result.txt
grep -qx OEM_DUAL_REVISION_REGISTERS_READ_AMPS_UNBOUND_RESET_LOW_NO_PCM /tmp/k102-amp-readonly-ids/result.txt
dir=/tmp/k102-checkpoint
test ! -e "$dir"
mkdir -m700 "$dir" "$dir/tests"
{
    uname -a
    cat /proc/sys/kernel/random/boot_id /proc/uptime /proc/sys/kernel/tainted
    cat "$mpss/state" "$adsp/state"
} > "$dir/state.txt"
/usr/sbin/wpa_cli -p/run/samurai-wifi/wpa-control -iwlan0 status > "$dir/wifi-status.txt"
grep -qx wpa_state=COMPLETED "$dir/wifi-status.txt"
grep -qx freq=5180 "$dir/wifi-status.txt"
ls -A /sys/class/bluetooth > "$dir/bt-class.txt"
[ ! -s "$dir/bt-class.txt" ]
cat /sys/bus/aprbus/devices/*/samurai_api > "$dir/native-api.txt"
cat /proc/asound/cards > "$dir/alsa-cards.txt"
cat "$(/tmp/k102-haptics-device)/status" > "$dir/haptics-status.txt"
cat /sys/kernel/debug/asoc/components > "$dir/codec-components.txt"
cat /sys/kernel/debug/gpio > "$dir/gpio.txt"
cat /sys/kernel/debug/pinctrl/3100000.pinctrl/pinmux-pins > "$dir/pinmux.txt"
cat /sys/kernel/debug/devices_deferred > "$dir/deferred.txt"
for p in /sys/bus/i2c/devices/*-0039 /sys/bus/i2c/devices/*-003a; do
    test -e "$p" || continue
    [ "$(readlink -f "$p/of_node/..")" = /sys/firmware/devicetree/base/soc@0/geniqup@8c0000/i2c@890000 ]
    test ! -L "$p/driver"
done
cat /sys/kernel/debug/dri/1/encoder-0/status > "$dir/encoder-status.txt"
cat /proc/modules > "$dir/modules.txt"
cat /proc/mounts > "$dir/mounts.txt"
ps > "$dir/processes.txt"
/usr/sbin/qrtr-lookup > "$dir/qrtr.txt"
/usr/sbin/samurai-radio-address status > "$dir/address-status.txt"
cp -a /run/samurai-radio-address "$dir/"
cp /run/samurai-wifi-boot.log /run/samurai-bluetooth-boot.log "$dir/"
cp /run/samurai-wifi/boot-finished /run/samurai-wifi/nv-source-hashes.txt "$dir/"
sha256sum -c /run/samurai-wifi/nv-source-hashes.txt > "$dir/nv-source-check.txt"
sha256sum /dev/sda2 > "$dir/persist-after.sha"
sha256sum /dev/sde11 /dev/sde32 /dev/sde17 /init /usr/sbin/samurai-* /lib/modules/samurai/*.ko > "$dir/deployment.sha"
cp /sys/firmware/fdt "$dir/runtime-fdt.bin"
cp -a /tmp/k102-audio-runtime /tmp/k102-audio-runtime-retry1 /tmp/k102-auto-network-completion /tmp/k102-amp-readonly-ids "$dir/tests/"
dmesg > "$dir/dmesg.txt"
[ "$(cat /proc/sys/kernel/tainted)" = 0 ]
echo WCD934X_AND_DUAL_MAX98937_IDS_AUTO_WIFI_CHECKPOINT_PASS > "$dir/result.txt"
(cd "$dir" && find . -type f ! -path ./SHA256SUMS -exec sha256sum '{}' ';') > "$dir/SHA256SUMS"
tar -C /tmp -cf /tmp/k102-checkpoint.tar k102-checkpoint
sha256sum /tmp/k102-checkpoint.tar
