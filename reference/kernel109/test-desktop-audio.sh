#!/bin/sh
set -eu
umask 077
test "$(cat /etc/samurai-rootfs-stage)" = kernel109
dest=/var/lib/samurai/k109-desktop-audio-first
test ! -e "$dest"
mkdir "$dest"
snapshot() {
    cat /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status
    cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status
}
snapshot > "$dest/before.txt"
sha256sum /tmp/k109-tone-low-private.wav > "$dest/tone-input.sha256"
su -s /bin/sh cy122 -c 'XDG_RUNTIME_DIR=/run/user/10000 paplay --device=alsa_output.platform-sound.HiFi__Speaker__sink --volume=16384 /tmp/k109-tone-low-private.wav' > "$dest/play.txt" 2>&1 &
child=$!
sleep 1
snapshot > "$dest/play-live.txt"
if wait "$child"; then echo 0 > "$dest/play-exit.txt"; else echo "$?" > "$dest/play-exit.txt"; fi
timeout -s TERM 5 su -s /bin/sh cy122 -c 'XDG_RUNTIME_DIR=/run/user/10000 parec --device=alsa_input.platform-sound.HiFi__Mic__source --raw --format=s16le --rate=48000 --channels=1 --latency-msec=20' > "$dest/mic-private.s16le" 2> "$dest/capture.txt" &
child=$!
sleep 1
snapshot > "$dest/capture-live.txt"
if wait "$child"; then echo 0 > "$dest/capture-exit.txt"; else echo "$?" > "$dest/capture-exit.txt"; fi
sleep 7
snapshot > "$dest/after.txt"
dmesg > "$dest/dmesg.txt"
logread -n 0 -u pulseaudio > "$dest/pulse-log.txt"
cat /proc/sys/kernel/tainted > "$dest/tainted.txt"
tar -C "$dest" -cf /tmp/k109-desktop-audio-first.tar .
sha256sum /tmp/k109-desktop-audio-first.tar
cat "$dest/play-exit.txt" "$dest/capture-exit.txt" "$dest/after.txt"
echo BOUNDED_DESKTOP_AUDIO_CHECKPOINT_COMPLETE
