#!/bin/sh
set -eu
umask 077
prefix=${1:?capture prefix required}
case "$prefix" in *[!a-z0-9-]*|'') exit 2;; esac
uname -v | grep -q '^#113 '
dest=/var/lib/samurai/k113-desktop-$prefix
test ! -e "$dest"
mkdir "$dest"
test "$(cat /var/lib/samurai/persistence-test.txt)" = F2FS-K109-PERSISTENCE-TEST
rc-service greetd status > "$dest/greetd.txt"
nmcli -t -f GENERAL.STATE,GENERAL.CONNECTION device show wlan0 > "$dest/wlan.txt"
grep -q ':100 ' "$dest/wlan.txt"
sha256sum /sys/class/net/wlan0/address > "$dest/mac-hash.txt"
cmp "$dest/mac-hash.txt" /var/lib/samurai/k109-networkmanager-first/mac-before-hash.txt
curl -4 --interface wlan0 --fail --connect-timeout 10 --max-time 20 https://www.baidu.com/ -o "$dest/https-body.txt" > "$dest/https-status.txt" 2>&1
su -s /bin/sh cy122 -c 'XDG_RUNTIME_DIR=/run/user/10000 pactl list short sinks' > "$dest/sinks.txt"
su -s /bin/sh cy122 -c 'XDG_RUNTIME_DIR=/run/user/10000 pactl list short sources' > "$dest/sources.txt"
grep -q 'alsa_output.platform-sound.HiFi__Speaker__sink' "$dest/sinks.txt"
grep -q 'alsa_input.platform-sound.HiFi__Mic__source' "$dest/sources.txt"
cat /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status > "$dest/pcm-idle.txt"
test "$(cat "$dest/pcm-idle.txt")" = "$(printf 'closed\nclosed')"
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dest/amps.txt"
test "$(grep -c 'powered=0 muted=1' "$dest/amps.txt")" = 2
cat /sys/bus/i2c/devices/2-005a/status > "$dest/haptics.txt"
grep -q 'active=0 starts=0 stops=0 watchdog_stops=0 error=0' "$dest/haptics.txt"
chronyc tracking > "$dest/clock.txt"
grep -q 'Leap status.*Normal' "$dest/clock.txt"
ps -eo pid,user,args > "$dest/processes.txt"
grep -q '/etc/phosh/phoc.ini' "$dest/processes.txt"
logread -b list > "$dest/boots-private.txt"
dmesg > "$dest/dmesg.txt"
cat /proc/sys/kernel/tainted > "$dest/tainted.txt"
cat /proc/sys/kernel/random/boot_id > "$dest/boot-id-private.txt"
uname -a > "$dest/uname.txt"
cat /sys/devices/platform/sensor-power/state > "$dest/power-state.txt"
(cd "$dest" && find . -type f ! -name SHA256SUMS -exec sha256sum '{}' ';') > "$dest/SHA256SUMS"
tar -C "$dest" -cf "/tmp/k113-desktop-$prefix.tar" .
sha256sum "/tmp/k113-desktop-$prefix.tar"
echo PHOSH_WIFI_NTP_NATIVE_AUDIO_IDLE_AND_HAPTICS_PASS
