#!/bin/sh
set -eu
umask 077
test "$(cat /etc/samurai-rootfs-stage)" = kernel109
apk add /tmp/evtest-1.36-r0.apk /tmp/grim-1.5.0-r0.apk /tmp/stevia-schemas-0.57.0-r2.apk /tmp/wlr-randr-0.5.0-r1.apk
gsettings list-schemas | grep '^mobi.phosh.osk$'
# Keep haptics inactive while their validation is restricted to static evidence.
cat > /usr/share/glib-2.0/schemas/90_samurai_haptics.gschema.override <<'EOF'
[org.sigxcpu.feedbackd]
profile='silent'
allow-important=[]
max-haptic-strength=0.0
EOF
glib-compile-schemas --strict /usr/share/glib-2.0/schemas
sed -i '/^export GNOME_SESSION_AUTOSTART_DIR=/d' /usr/local/bin/samurai-phosh-session
date -u > /var/lib/samurai/k109-phosh-session/schemas-fixed
mv /home/cy122/.local/state/samurai-phosh-session.log /home/cy122/.local/state/samurai-phosh-session-first.log
if test -f /run/greetd.run; then
    mv /run/greetd.run /var/lib/samurai/k109-phosh-session/greetd-second-run-marker
fi
rc-service greetd start
sleep 15
rc-service greetd status
ps -eo pid,user,args | awk '$2 == "cy122" || /[p]hoc/'
grep -E 'osk|FD640|GL renderer|error|ERROR|CRITICAL|failed|Failed' /home/cy122/.local/state/samurai-phosh-session.log | head -40 || true
