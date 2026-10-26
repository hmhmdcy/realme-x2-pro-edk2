#!/bin/sh
set -eu
umask 077
test "$(cat /etc/samurai-rootfs-stage)" = kernel109
grep -q Realme-X2Pro-samurai /proc/asound/cards
dest=/usr/share/alsa/ucm2/conf.d/Realme_X2_Pro
test ! -e "$dest"
mkdir -p "$dest"
chmod 755 "$dest"
install -m 644 /tmp/k109-Realme_X2_Pro.conf "$dest/Realme_X2_Pro.conf"
install -m 644 /tmp/k109-HiFi.conf "$dest/HiFi.conf"
alsaucm -c hw:0 list _verbs > /var/lib/samurai/k109-ucm-verbs.txt
alsaucm -c hw:0 dump text > /var/lib/samurai/k109-ucm-dump.txt
cat /var/lib/samurai/k109-ucm-verbs.txt
# Retain the distribution's PulseAudio desktop owner. Its running instances
# need one restart to discover the new UCM profile; clients auto-spawn it.
su -s /bin/sh cy122 -c 'XDG_RUNTIME_DIR=/run/user/10000 pulseaudio --kill'
sleep 3
su -s /bin/sh cy122 -c 'XDG_RUNTIME_DIR=/run/user/10000 pactl list short sinks'
su -s /bin/sh cy122 -c 'XDG_RUNTIME_DIR=/run/user/10000 pactl list short sources'
echo UCM_NATIVE_PROFILE_INSTALLED
