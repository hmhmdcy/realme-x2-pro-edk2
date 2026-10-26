#!/bin/sh
set -eu
cat > /etc/init.d/samurai-loopback <<'EOF'
#!/sbin/openrc-run
description="Initialize loopback for the native persistent rootfs"
depend() {
    need sysfs
    before sshd dbus samurai-usb samurai-radio
}
start() {
    ebegin "Initializing loopback"
    ip link set dev lo up && ip address replace 127.0.0.1/8 dev lo
    eend $?
}
EOF
chmod 755 /etc/init.d/samurai-loopback
rc-update add samurai-loopback boot
rc-service samurai-loopback start
ip -4 addr show dev lo
echo LOOPBACK_CONFIGURED_PERSISTENTLY
