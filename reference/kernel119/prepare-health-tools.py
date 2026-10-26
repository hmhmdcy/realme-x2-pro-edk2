from pathlib import Path
root=Path('/mnt/e/RealmeX2Pro edk2/reference')
ref=root/'kernel119'
t=(root/'kernel115/stop-boot-traces.sh').read_text().replace('k115-boot-traces','k119-boot-traces').replace('/var/lib/samurai/k115-final-health/boot-id-private.txt','/var/lib/samurai/k119-first-runtime/boot-id-private.txt')
(ref/'stop-boot-traces.sh').write_text(t)
t=(root/'kernel118/observe-current-115.sh').read_text().replace('k118-current115-observation','k119-current118-observation').replace('/var/lib/samurai/k115-final-health/boot-id-private.txt','/var/lib/samurai/k119-first-runtime/boot-id-private.txt').replace('CURRENT115_READONLY','CURRENT118_READONLY')
t=t.replace('test -c /dev/dri/card0',"""card=$(readlink -f /dev/dri/by-path/platform-ae01000.display-controller-card)
test -c "$card"
""" ,1).replace('    test -c /dev/dri/card0','    test -c "$card"')
(ref/'observe-current-118.sh').write_text(t)
t=(root/'kernel118/finalize-current-health.sh').read_text().replace('k118-current115-observation','k119-current118-observation').replace('k118-current115-health-private','k119-current118-health-private').replace('CURRENT115_300','CURRENT118_300')
t=t.replace('test -c /dev/dri/card0',"""card=$(readlink -f /dev/dri/by-path/platform-ae01000.display-controller-card)
test -c "$card"
card_name=${card##*/}
minor=${card_name#card}
case "$minor" in *[!0-9]*|'') exit 2;; esac
cat /sys/kernel/debug/dri/$minor/state > "$dest/drm-state.txt"
cat /sys/kernel/debug/dri/$minor/clients > "$dest/drm-clients.txt"
printf '%s\\n' "$card_name" > "$dest/drm-card-name.txt"
"""
)
t=t.replace('/sys/class/drm/card0-DSI-1/status','/sys/class/drm/$card_name-DSI-1/status')
t=t.replace('cd "$dest"',"""sha256sum /dev/sde11 /dev/sde32 /dev/sda2 > "$dest/partition-check.sha256"
cat /sys/class/remoteproc/remoteproc1/state /sys/class/remoteproc/remoteproc2/state > "$dest/radio-audio.txt"
timeout 10 mmcli -m 0 -J > "$dest/modem-private.json" 2>&1 || true
cp /home/cy122/.local/state/samurai-phosh-session.log "$dest/phosh-session-private.txt"
cd "$dest"
"""
)
(ref/'finalize-current-health.sh').write_text(t)
print('K119_BOOT_TRACE_PRESERVATION_AND_DYNAMIC_OWN_DRM_HEALTH_TOOLS_READY')
