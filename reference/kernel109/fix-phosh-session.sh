#!/bin/sh
set -eu
umask 077
test "$(cat /etc/samurai-rootfs-stage)" = kernel109
mkdir -p /var/lib/samurai/k109-phosh-session /etc/phosh
cp /etc/greetd/samurai-phosh.toml /var/lib/samurai/k109-phosh-session/greetd-before.toml
cat > /etc/greetd/samurai-phosh.toml <<'EOF'
[terminal]
vt = 7

[default_session]
command = "/usr/libexec/phrog-greetd-session"
user = "greetd"

[initial_session]
command = "/usr/bin/phosh-session"
user = "cy122"
EOF
cat > /etc/phosh/phoc.ini <<'EOF'
[output:DSI-1]
scale = 3
EOF
chown 10000:10000 /home/cy122/.config
chmod 700 /home/cy122/.config
cat /usr/libexec/phrog-greetd-session
rc-service greetd zap
rc-service greetd start
sleep 8
rc-service greetd status || true
ps -eo pid,user,args
ls -ld /run/user/10000 /home/cy122/.config || true
find /var/log -maxdepth 2 -type f -name '*greet*' -o -name '*phosh*'
echo PHOSH_SESSION_CONFIG_FIXED
