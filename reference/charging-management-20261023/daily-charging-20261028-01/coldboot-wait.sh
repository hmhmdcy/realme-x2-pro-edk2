#!/bin/bash
set -u

cp /mnt/e/edk2-samurai-out/kernel72/id_ed25519 /tmp/rmx-key
chmod 600 /tmp/rmx-key
ssh -i /tmp/rmx-key \
    -o UserKnownHostsFile=/mnt/e/edk2-samurai-out/kernel109/known_hosts-pmos \
    root@169.254.42.1 reboot >/dev/null 2>&1 || true
sleep 25
for i in $(seq 1 90); do
    if ssh -i /tmp/rmx-key \
        -o UserKnownHostsFile=/mnt/e/edk2-samurai-out/kernel109/known_hosts-pmos \
        -o ConnectTimeout=3 root@169.254.42.1 true 2>/dev/null; then
        echo "ssh_ready_attempt=$i"
        break
    fi
    sleep 3
done
echo waiting_for_default_runlevel
sleep 120
ssh -i /tmp/rmx-key \
    -o UserKnownHostsFile=/mnt/e/edk2-samurai-out/kernel109/known_hosts-pmos \
    root@169.254.42.1 \
    'sh /root/postboot-debug.sh; echo verify:; python3 /root/daily-verify.py || true; echo taint=$(cat /proc/sys/kernel/tainted)'
