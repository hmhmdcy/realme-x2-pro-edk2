#!/bin/sh
set -eu
umask 077
prefix=${1:?unique capture prefix required}
case "$prefix" in *[!a-z0-9-]*|'') exit 2;; esac
dest=/var/lib/samurai/k109-phosh-$prefix
test ! -e "$dest"
mkdir "$dest"
dmesg > "$dest/dmesg.txt"
logread -n 0 > "$dest/syslog.txt"
cp /home/cy122/.local/state/samurai-phosh-session.log "$dest/session.txt"
ps -eo pid,user,args > "$dest/processes.txt"
ls -la /run/user/10000 > "$dest/runtime.txt"
su -s /bin/sh cy122 -c 'XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0 wlr-randr' > "$dest/outputs.txt" 2>&1 || true
screen=/home/cy122/.local/state/samurai-phosh-screen-$prefix.png
test ! -e "$screen"
su -s /bin/sh cy122 -c "XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0 grim '$screen'" > "$dest/screenshot-status.txt" 2>&1 || true
if test -f "$screen"; then
    cp "$screen" "$dest/screen.png"
fi
for node in /sys/kernel/debug/dri/1/encoder* /sys/kernel/debug/dri/1/state; do
    test ! -f "$node" || cat "$node" > "$dest/$(basename "$node").txt"
done
cat /proc/sys/kernel/tainted > "$dest/tainted.txt"
tar -C "$dest" -cf "/tmp/k109-phosh-$prefix.tar" .
sha256sum "/tmp/k109-phosh-$prefix.tar"
cat "$dest/outputs.txt" "$dest/screenshot-status.txt"
