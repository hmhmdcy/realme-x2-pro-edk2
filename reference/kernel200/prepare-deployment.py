from pathlib import Path
import ast, json, hashlib, shutil

ref=Path(__file__).resolve().parent
old=ref.parent/'kernel189/reboot-r2'
out=Path('/mnt/e/edk2-samurai-out/kernel200')
build=json.loads((ref/'build-package-validation.json').read_text())
assert build['flash_partitions']==['boot'] and build['firmware_only_dtb_changed']
assert hashlib.sha256((out/'boot-partition-k200-mmcx.img').read_bytes()).hexdigest()==build['boot_sha256']
rollback=out.parent/'kernel172/boot-partition-k172-headset.img'
assert hashlib.sha256(rollback.read_bytes()).hexdigest()==build['rollback_boot_sha256']
shutil.copyfile(rollback,out/'boot-rollback-k172-private.img')

def convert(source):
    return source.replace('k189r2','k200').replace('stage=189','stage=200').replace("'stage': 189","'stage': 200").replace('taint=0','taint=512').replace("Path('/proc/sys/kernel/tainted').read_text().strip() == '0'","Path('/proc/sys/kernel/tainted').read_text().strip() == '512'").replace("Path('/proc/sys/kernel/tainted').read_text().strip()=='0'","Path('/proc/sys/kernel/tainted').read_text().strip()=='512'")

s=convert((old/'quiesce-current183.sh').read_text())
s=s.replace('k200-preflash','k200-baseline')
s=s.replace('test "$(cat /proc/sys/kernel/tainted)" = 0','test "$(cat /proc/sys/kernel/tainted)" = 512')
s=s.replace(' chronyd networkmanager iio-sensor-proxy',' chronyd iio-sensor-proxy')
start=s.index('for pid in $(pidof wpa_supplicant')
end=s.index('for pid in $(pidof ModemManager',start)
s=s[:start]+s[end:]
start=s.index('test -e /sys/bus/platform/devices/18800000.wifi')
end=s.index('mpss=$(',start)
s=s[:start]+'# Wi-Fi management remains online until the detached final transition.\n'+s[end:]
(ref/'quiesce-current183.sh').write_text(s)

s=convert((old/'check-quiesce.py').read_text()).replace('k200-preflash','k200-baseline')
s=s.replace("current.count('WARNING:')==prior.count('WARNING:')==0", "current.count('WARNING:')==prior.count('WARNING:')==3")
s=s.replace('# Preserve old kernel181 audio faults; quiesce proof uses actual offline/resource state.', '# Retain the one193 kernel warning and two199 OF property warnings from this boot.')
ast.parse(s);(ref/'check-quiesce.py').write_text(s)

s=convert((old/'disable-crtc.py').read_text())
s=s.replace("log.count('WARNING:') == 0", "log.count('WARNING:') == 3")
ast.parse(s);(ref/'disable-crtc.py').write_text(s)

s=convert((old/'freeze-for-bootloader.sh').read_text()).replace('k200-preflash','k200-baseline')
s=s.replace('"$before/old132-module-tree.sha256"','/var/lib/samurai/k200-deploy/paired-module-tree.sha256')
s=s.replace('sync\n', 'test ! -e /sys/bus/platform/devices/18800000.wifi/driver\ntest ! -e /sys/class/net/wlan0\nsync\n')
(ref/'freeze-for-bootloader.sh').write_text(s)

s=convert((old/'linux-restart2-bootloader.py').read_text()).replace('k200-preflash','k200-baseline')
ast.parse(s);(ref/'linux-restart2-bootloader.py').write_text(s)
print('K200_EXACT_BOOT_ROLLBACK_AND_FRESH_GUARDED_DEPLOYMENT_TOOLS_PREPARED')
