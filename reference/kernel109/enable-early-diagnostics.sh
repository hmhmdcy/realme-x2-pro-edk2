#!/bin/sh
set -eu
umask 077
test "$(cat /etc/samurai-rootfs-stage)" = kernel109
mkdir /var/lib/samurai/k109-early-diagnostics-before
cp /etc/rc.conf /etc/conf.d/sshd /var/lib/samurai/k109-early-diagnostics-before/
# A slow default-runlevel radio/UI must not delay the diagnostic transport.
for service in samurai-usb sshd; do
    rc-update add "$service" boot
    if test -L "/etc/runlevels/default/$service"; then rc-update del "$service" default; fi
done
cat >> /etc/conf.d/sshd <<'EOF'

# SSH is usable in the boot runlevel before desktop/radio startup.
rc_need="samurai-usb"
EOF
cat >> /etc/rc.conf <<'EOF'

# Preserve boot service progress for persistent-rootfs diagnostics.
rc_logger="YES"
rc_log_path="/var/log/rc.log"
EOF
/usr/sbin/sshd.pam -t
sync
echo NCM_SSH_BOOT_RUNLEVEL_AND_RC_LOGGING_ENABLED
