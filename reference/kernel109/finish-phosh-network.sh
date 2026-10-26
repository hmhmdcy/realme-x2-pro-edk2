#!/bin/sh
set -eu
umask 077
test "$(cat /etc/samurai-rootfs-stage)" = kernel109
cat >> /etc/conf.d/chronyd <<'EOF'

# WLAN is prepared by Samurai radio and managed by NetworkManager.
rc_need="networkmanager"
FAST_STARTUP=yes
EOF
rc-service chronyd start
if test -f /etc/ssh/sshd_config.d/00-samurai-apk-tunnel.conf; then
    mv /etc/ssh/sshd_config.d/00-samurai-apk-tunnel.conf /var/lib/samurai/k109-apk-tunnel-used.conf
fi
/usr/sbin/sshd.pam -t
rc-service sshd reload
test ! -e /etc/ssh/sshd_config.d/00-samurai-apk-tunnel.conf
sync
echo CHRONY_STARTED_AND_TEMPORARY_SSH_FORWARD_RULE_REMOVED
