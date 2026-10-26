#!/bin/sh
set -eu
[ "$(cat /proc/sys/kernel/random/boot_id)" = dfe8e722-f6b7-4ce8-85cc-17dfba80f69d ]
test ! -e /tmp/k91-handshake-tx-dmesg.txt
param=/sys/module/ath10k_core/parameters/debug_mask
previous=$(cat "$param")
trap 'echo "$previous" > "$param"; /tmp/k91-wpa_cli -p/tmp/k91-wpa-ctrl -iwlan0 log_level DEBUG >/dev/null 2>&1' EXIT
dmesg > /tmp/k91-handshake-tx-before.txt
# HTT and MAC event text only; packet dump flags remain disabled.
echo 24 > "$param"
/tmp/k91-wpa_cli -p/tmp/k91-wpa-ctrl -iwlan0 log_level MSGDUMP
/tmp/k91-wpa_cli -p/tmp/k91-wpa-ctrl -iwlan0 disable_network 0
/tmp/k91-wpa_cli -p/tmp/k91-wpa-ctrl -iwlan0 enable_network 0
/tmp/k91-wpa_cli -p/tmp/k91-wpa-ctrl -iwlan0 reassociate
sleep 15
echo "$previous" > "$param"
dmesg > /tmp/k91-handshake-tx-dmesg.txt
cp /tmp/k91-wpa-observed.log /tmp/k91-handshake-wpa.txt
grep 'htt tx completion msdu_id' /tmp/k91-handshake-tx-dmesg.txt | sed -E 's/.*status ([0-9]+).*/\1/' | sort | uniq -c
/tmp/k91-wpa_cli -p/tmp/k91-wpa-ctrl -iwlan0 status > /tmp/k91-handshake-final-status.txt
grep -E '^(wpa_state|freq|key_mgmt|pairwise_cipher|group_cipher)=' /tmp/k91-handshake-final-status.txt
sha256sum /tmp/k91-handshake-tx-dmesg.txt /tmp/k91-handshake-wpa.txt
cat /proc/sys/kernel/tainted /sys/class/remoteproc/remoteproc0/state
