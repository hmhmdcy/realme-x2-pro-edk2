#!/bin/sh
set -eu
[ "$(cat /proc/sys/kernel/random/boot_id)" = dfe8e722-f6b7-4ce8-85cc-17dfba80f69d ]
printf '%s\n' '39bee3e48a11407adea4e7cd415e48c2b6409b75b6c133df787341991d93d5fa  /tmp/k91-wpa_supplicant' 'd0823f055d1e0506f8baaeede9d2bcd333f43bb9bd1195179ecc61ccfce9e2a4  /tmp/k91-wpa_cli' '8fce2f35f5b621f52d434be6d8af8d379ccecc6c892068c8bf653391f92f7ff3  /tmp/k91-wpa_passphrase' | sha256sum -c -
chmod 700 /tmp/k91-wpa_supplicant /tmp/k91-wpa_cli /tmp/k91-wpa_passphrase
test ! -e /tmp/k91-wpa.pid
umask 077
printf 'ctrl_interface=/tmp/k91-wpa-ctrl\n' > /tmp/k91-wpa.conf
/tmp/k91-wpa_supplicant -v
/tmp/k91-wpa_supplicant -B -Dnl80211 -iwlan0 -c/tmp/k91-wpa.conf -P/tmp/k91-wpa.pid > /tmp/k91-wpa.log 2>&1
/tmp/k91-wpa_cli -p/tmp/k91-wpa-ctrl -iwlan0 ping
/tmp/k91-wpa_cli -p/tmp/k91-wpa-ctrl -iwlan0 get_capability key_mgmt
# Synthetic published WPA-PSK test vector, unrelated to any local AP.
printf 'password\n' | /tmp/k91-wpa_passphrase IEEE > /tmp/k91-wpa-vector.txt
grep -q 'psk=f42c6fc52df0ebef9ebb4b90b38a5f902e83fe1b135a70e23aed762e9710a12e' /tmp/k91-wpa-vector.txt
printf 'Synthetic WPA-PSK vector: OK\n'
cat /proc/sys/kernel/tainted /sys/class/remoteproc/remoteproc0/state
