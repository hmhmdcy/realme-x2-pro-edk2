#!/bin/sh
# Post-flash acceptance: NCM link must come up by itself on boot and accept SSH.
# Runs on an already-set Windows/WSL host with the USB cable attached.
set -u

KEY=${KEY:-/tmp/k}
KNOWN=${KNOWN:-/mnt/c/Users/cy122/.ssh/samurai_usb_known_hosts}
GUEST=${GUEST:-root@172.16.42.1}
TIMEOUT=${TIMEOUT:-180}

if [ ! -f "$KEY" ]; then
    cp /mnt/c/Users/cy122/.ssh/samurai_id_ed25519 "$KEY"
    chmod 600 "$KEY"
fi

iface=""
i=0
while [ "$i" -lt 60 ]; do
    iface=$(ip -br link | awk '/^usb0$/ {print $1}' | head -1)
    [ -z "$iface" ] && iface=$(ip -br link | awk '/enp|usb/ {print $1}' | grep -v eth0 | head -1)
    [ -n "$iface" ] && break
    i=$((i + 1))
    sleep 1
done

printf 'interface=%s\n' "${iface:-none}"

deadline=$(( $(date +%s) + TIMEOUT ))
while [ "$(date +%s)" -lt "$deadline" ]; do
    if ping -c 1 -W 2 172.16.42.1 >/dev/null 2>&1; then
        break
    fi
    sleep 3
done

if ! ping -c 1 -W 2 172.16.42.1 >/dev/null 2>&1; then
    printf 'RESULT=FAIL reason=ncm_no_icmp\n'
    exit 1
fi

ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new \
    -o UserKnownHostsFile="$KNOWN" -o ConnectTimeout=15 -i "$KEY" \
    "$GUEST" 'printf "guest_boot_id=%s\n" "$(cat /proc/sys/kernel/random/boot_id)"
              printf "guest_kernel=%s\n" "$(uname -r)"
              printf "guest_rootfs_uuid=%s\n" "$(blkid -s UUID -o value /dev/sda16)"
              printf "guest_packages=%s\n" "$(grep -c "^P:" /lib/apk/db/installed)"
              printf "guest_ncm_mode=%s\n" "$(grep default_mode /etc/usb-signaller.d/90-samurai.toml)"
              printf "guest_sshd=%s\n" "$(rc-service sshd status 2>&1 | head -1)"
              printf "guest_usb0=%s\n" "$(ip -4 addr show usb0 2>/dev/null | awk "/inet /{print \$2}")"'
rc=$?
if [ "$rc" -ne 0 ]; then
    printf 'RESULT=FAIL reason=ncm_icmp_ok_ssh_failed\n'
    exit 1
fi

printf 'RESULT=PASS ncm_ssh=ok\n'
