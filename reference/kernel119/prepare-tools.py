from pathlib import Path
root=Path('/mnt/e/RealmeX2Pro edk2/reference')
ref=root/'kernel119';out=Path('/mnt/e/edk2-samurai-out/kernel119')
out.mkdir(mode=0o700,exist_ok=True)
text=(root/'kernel113/collect-preflash.sh').read_text()
text=text.replace("'^#112 '","'^#115 '").replace('/var/lib/samurai/k112-reboot-radio-clean-2/boot-id-private.txt','/var/lib/samurai/k115-final-health/boot-id-private.txt').replace('k113-preflash','k119-preflash').replace('KERNEL113_PREFLASH','KERNEL119_PREFLASH')
text=text.replace('grep -q \'^/dev/sda16 / f2fs rw\' /proc/mounts',"""grep -q '^/dev/sda16 / f2fs rw' /proc/mounts
test "$(id -u cy122)" = 10000
pgrep -x phosh >/dev/null
pgrep -x phoc >/dev/null
test -c /dev/dri/card0
test -c /dev/dri/renderD128
test "$(cat /sys/devices/platform/sensor-power/state)" = 'vdd=0 vddio=0'""")
text=text.replace('cat /proc/uptime',"""sha256sum -c /var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256 > "$dest/vendor-check.txt"
sha256sum /lib/modules/7.3.0-rc6-rmx1931-samurai+/kernel/drivers/net/ipa/ipa.ko > "$dest/ipa-module.sha256"
pgrep -x phosh > "$dest/phosh.txt"
pgrep -x phoc > "$dest/phoc.txt"
cat /sys/class/drm/card0-DSI-1/status > "$dest/connector.txt"
cat /sys/class/remoteproc/remoteproc0/state /sys/devices/platform/sensor-power/state > "$dest/sensors.txt"
cat /sys/kernel/tracing/instances/display/tracing_on /sys/kernel/tracing/instances/radio/tracing_on > "$dest/traces.txt"
cat /proc/asound/card0/pcm0p/sub0/status /proc/asound/card0/pcm1c/sub0/status > "$dest/pcm.txt"
cat /sys/bus/i2c/devices/1-0039/status /sys/bus/i2c/devices/1-003a/status > "$dest/amps.txt"
cat /proc/uptime""")
(ref/'collect-preflash.sh').write_text(text)
text=(root/'kernel115/quiesce-clean-115.sh').read_text()
text=text.replace('/var/lib/samurai/k115-first-runtime/boot-id-private.txt','/var/lib/samurai/k119-preflash/boot-id-private.txt').replace('kernel/tainted)" = 512','kernel/tainted)" = 0').replace('k115-$prefix','k119-$prefix')
text=text.replace('test -z "$(pgrep -u 10000 || true)"','test -z "$(pgrep -u 10000 || true)"\ntest -z "$(pgrep -x phosh || true)"\ntest -z "$(pgrep -x phoc || true)"',1)
text=text.replace('cat /proc/uptime',"""sha256sum -c /var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256 > "$dest/vendor-check.txt"
cat /proc/uptime""")
(ref/'quiesce-clean.sh').write_text(text)
text=(root/'kernel115/freeze-for-bootloader.sh').read_text()
text=text.replace("'^#113 '","'^#115 '").replace('kernel/tainted)" = 512','kernel/tainted)" = 0').replace('k115-preflash','k119-preflash').replace('k115-flash-quiesce','k119-flash-quiesce').replace('k115-preflash-partition','k119-preflash-partition').replace('k115-preflash-nv','k119-preflash-nv').replace('k115-bootloader-state','k119-bootloader-state').replace('KERNEL115_F2FS','KERNEL119_F2FS')
text=text.replace('test -e /var/lib/samurai/k115-runtime-stage/package-check.txt',"""test -e /var/lib/samurai/k115-runtime-stage/package-check.txt
test "$(cat /var/lib/samurai/k119-flash-quiesce/boot-id-private.txt)" = "$1"
test -z "$(pgrep -x phosh || true)"
test -z "$(pgrep -x phoc || true)"
test -z "$(pidof ModemManager || true)"
test ! -e /proc/asound/card0""")
(ref/'freeze-for-bootloader.sh').write_text(text)
text=(root/'kernel115/enter-bootloader.ps1').read_text().replace('kernel115','kernel119').replace('k115','k119').replace('KERNEL115','KERNEL119')
(ref/'enter-bootloader.ps1').write_text(text)
text=(root/'kernel115/enable-eud.ps1').read_text().replace('kernel115','kernel119').replace('KERNEL115','KERNEL119')
(ref/'enable-eud.ps1').write_text(text)
print('K119_CURRENT115_PRECHECK_QUIESCE_FREEZE_F1_TOOLS_PREPARED')
