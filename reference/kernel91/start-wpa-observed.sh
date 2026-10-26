#!/bin/sh
set -eu
[ "$(cat /proc/sys/kernel/random/boot_id)" = dfe8e722-f6b7-4ce8-85cc-17dfba80f69d ]
echo '39bee3e48a11407adea4e7cd415e48c2b6409b75b6c133df787341991d93d5fa  /tmp/k91-wpa_supplicant' | sha256sum -c -
if [ -e /tmp/k91-wpa.pid ]; then
    old_pid=$(cat /tmp/k91-wpa.pid)
    case "$old_pid" in ''|*[!0-9]*) exit 1;; esac
    tr '\0' ' ' < "/proc/$old_pid/cmdline" | grep -q '^/tmp/k91-wpa_supplicant '
    /tmp/k91-wpa_cli -p/tmp/k91-wpa-ctrl -iwlan0 terminate
    for attempt in 1 2 3 4 5; do
        kill -0 "$old_pid" 2>/dev/null || break
        sleep 1
    done
    ! kill -0 "$old_pid" 2>/dev/null
    rm -f /tmp/k91-wpa.pid
fi
test ! -e /tmp/k91-wpa.pid
test -f /tmp/k91-wpa.conf
umask 077
# Keep the foreground process under nohup so every runtime event reaches the
# private log. This build has no optional -f file-logging switch.
nohup /tmp/k91-wpa_supplicant -dd -Dnl80211 -iwlan0 -c/tmp/k91-wpa.conf > /tmp/k91-wpa-observed.log 2>&1 < /dev/null &
echo $! > /tmp/k91-wpa.pid
sleep 1
kill -0 "$(cat /tmp/k91-wpa.pid)"
/tmp/k91-wpa_cli -p/tmp/k91-wpa-ctrl -iwlan0 ping
