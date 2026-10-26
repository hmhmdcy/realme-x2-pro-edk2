#!/bin/sh
set -eu
umask 077
dest=/usr/share/alsa/ucm2/conf.d/Realme_X2_Pro
cp "$dest/HiFi.conf" /var/lib/samurai/k109-ucm-hifi-first.conf
install -m 644 /tmp/k109-HiFi.conf "$dest/HiFi.conf"
mkdir -p /etc/pulse/daemon.conf.d
chmod 755 /etc/pulse/daemon.conf.d
cat > /etc/pulse/daemon.conf.d/90-samurai.conf <<'EOF'
default-sample-format = s16le
default-sample-rate = 48000
alternate-sample-rate = 48000
default-fragments = 4
default-fragment-size-msec = 20
EOF
chmod 644 /etc/pulse/daemon.conf.d/90-samurai.conf
su -s /bin/sh cy122 -c 'XDG_RUNTIME_DIR=/run/user/10000 pulseaudio --kill'
sleep 4
su -s /bin/sh cy122 -c 'XDG_RUNTIME_DIR=/run/user/10000 pactl list short sinks'
su -s /bin/sh cy122 -c 'XDG_RUNTIME_DIR=/run/user/10000 pactl list short sources'
cat /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status
echo UCM_FE_BACKEND_PROBE_FIX_INSTALLED
