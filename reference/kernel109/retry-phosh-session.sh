#!/bin/sh
set -eu
umask 077
test "$(cat /etc/samurai-rootfs-stage)" = kernel109
rc-service greetd stop
mkdir -p /home/cy122/.local/state /usr/local/bin
chown 10000:10000 /home/cy122/.local /home/cy122/.local/state
cat > /usr/local/bin/samurai-phosh-session <<'EOF'
#!/bin/sh
umask 077
mkdir -p "$HOME/.local/state"
export XDG_CURRENT_DESKTOP=Phosh:GNOME
exec >> "$HOME/.local/state/samurai-phosh-session.log" 2>&1
date -u
exec /usr/bin/phosh-session
EOF
chmod 755 /usr/local/bin/samurai-phosh-session
sed -i 's@command = "/usr/bin/phosh-session"@command = "/usr/local/bin/samurai-phosh-session"@' /etc/greetd/samurai-phosh.toml
# greetd deliberately runs the initial session only once per boot. Preserve its
# marker before this one controlled retry, so the corrected command can run.
if test -f /run/greetd.run; then
    mv /run/greetd.run /var/lib/samurai/k109-phosh-session/greetd-first-run-marker
fi
rc-service greetd start
sleep 12
rc-service greetd status
tail -100 /home/cy122/.local/state/samurai-phosh-session.log
ps -eo pid,user,args | awk '$2 == "cy122" || /[p]hoc/'
