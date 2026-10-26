#!/bin/sh
set -eu
umask 077
file=/etc/ssh/sshd_config.d/00-samurai-apk-tunnel.conf
test ! -e "$file"
cat > "$file" <<'EOF'
# Temporary repository downloads over the existing USB SSH connection.
Match User root
    AllowTcpForwarding remote
    PermitListen 127.0.0.1:18080
Match all
EOF
/usr/sbin/sshd.pam -t
/usr/sbin/sshd.pam -T -C user=root,host=samurai,addr=169.254.191.135 | grep -iE '^(allowtcpforwarding|permitlisten) '
rc-service sshd reload
echo TEMPORARY_EXACT_LOOPBACK_REMOTE_FORWARDING_READY
