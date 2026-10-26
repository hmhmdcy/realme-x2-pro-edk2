"""Fresh identity, exact rollback and userspace inventory before any change."""
from pathlib import Path
import dbus
import hashlib
import json
import os
import struct
import subprocess

os.umask(0o077)
root = Path('/var/lib/samurai')
out = root / 'k233-baseline'
assert not out.exists()
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == (root / 'k230-runtime/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
assert {p.parent.name:p.read_text().strip() for p in Path('/sys/module').glob('*/taint') if p.read_text().strip()}=={}
assert Path('/sys/firmware/devicetree/base/model').read_bytes() == b'Realme X2 Pro (RMX1931CN)\0'
out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_bytes(boot)
(out / 'start-uptime-private.txt').write_text(Path('/proc/uptime').read_text())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
module_root = Path('/usr/lib/modules') / os.uname().release
module = module_root / 'kernel/drivers/misc/fastrpc.ko'
assert sha(module) == '2abde0ead81c2feb78f639da2ab29d7c3e29654a9d013a098418b232a5cfd794'
original = module.read_bytes()
(out / 'fastrpc-default-intree-private.ko').write_bytes(original)


def note(data):
    offset = struct.unpack_from('<Q', data, 40)[0]
    size, count, index = struct.unpack_from('<HHH', data, 58)
    sections = [struct.unpack_from('<IIQQQQIIQQ', data, offset + i * size) for i in range(count)]
    strings = data[sections[index][4]:sections[index][4] + sections[index][5]]
    found = [data[s[4]:s[4] + s[5]] for s in sections if strings[s[0]:].split(b'\0', 1)[0] == b'.note.gnu.build-id']
    assert len(found) == 1
    return found[0]


assert subprocess.check_output(['modinfo','-F','intree',str(module)],text=True).strip()=='Y'
loaded=Path('/sys/module/fastrpc/notes/.note.gnu.build-id').read_bytes()
assert loaded==note(original)
(out/'fastrpc-default-note-private.bin').write_bytes(note(original))
(out/'fastrpc-loaded-note-private.bin').write_bytes(loaded)
modules = {str(p.relative_to(module_root)): sha(p) for p in module_root.rglob('*') if p.is_file()}
assert len([n for n in modules if n.endswith('.ko')]) == 772
assert modules['kernel/drivers/media/i2c/imx471.ko'] == 'e49dab26b05a325df8da64bb5c4b57c29cd51d1dcf15f5d4ed4dcb53033e66f1'
assert modules['kernel/drivers/media/platform/qcom/camss/qcom-camss.ko'] == 'fae1ed40da4e2751c081aca3a990a5a3c44de47599883a045340b9f62f54803e'
(out / 'module-inventory-private.json').write_text(json.dumps(modules, indent=2) + '\n')
(out / 'module-tree.sha256').write_text(''.join(v + '  ' + n + '\n' for n, v in sorted(modules.items())))
installed = Path('/lib/apk/db/installed').read_bytes()
(out / 'installed-before-private.txt').write_bytes(installed)
assert b'V:99990.7.2-r13\n' in installed and b'V:0.1.0-r8\n' in installed
programs = ['/usr/sbin/samurai-ssc', '/usr/libexec/samurai-hexagonrpcd', '/usr/bin/ModemManager',
            '/usr/sbin/samurai-bluetooth', '/usr/sbin/samurai-wifi', '/usr/sbin/samurai-gnss-assist',
            '/usr/sbin/samurai-tqftpserv', '/usr/sbin/samurai-modem-configs',
            '/etc/libcamera/configuration.yaml', '/etc/modules-load.d/samurai-camera-heaps.conf',
            '/etc/udev/rules.d/70-samurai-camera-heaps.rules']
hashes = {n: sha(n) for n in programs}
assert hashes['/usr/sbin/samurai-ssc'] == '9a1fd03f5f8e6f1b893f75465b01d1097419b06d41eaa24438aa1b63ee2f287c'
assert hashes['/usr/bin/ModemManager'] == 'b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc'
(out / 'userspace-check.sha256').write_text(''.join(v + '  ' + n + '\n' for n, v in sorted(hashes.items())))
persist = json.loads((root / 'k200-runtime/partition-hashes-private.json').read_text())['persist']
parts = {}
for dev, label, digest in [('sde11', 'boot', '156f0370fff6a65babc14738a62e4e2291594fe74f680cf3f62317dd0291198a'),
                            ('sde32', 'logdump', 'e73754c7d327925acf031aed54e0e6d02069b7a112c32b187ac9bfb468da1358'),
                            ('sda2', 'persist', persist)]:
    path = '/dev/' + dev
    assert subprocess.check_output(['lsblk', '-ndo', 'PARTLABEL', path], text=True).strip() == label
    value = subprocess.check_output(['sha256sum', path], text=True, timeout=30).split()[0]
    assert value == digest
    parts[path] = value
(out / 'partition-check.sha256').write_text(''.join(v + '  ' + n + '\n' for n, v in parts.items()))
with (out / 'nv-check-private.txt').open('wb') as output:
    subprocess.run(['sha256sum', '-c', '/run/samurai-wifi/nv-source-hashes.txt'], stdout=output, stderr=subprocess.STDOUT, check=True)
bus = dbus.SystemBus(private=True)
manager = bus.get_object('org.freedesktop.ModemManager1', '/org/freedesktop/ModemManager1')
objects = dbus.Interface(manager, 'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
paths = [p for p, v in objects.items() if 'org.freedesktop.ModemManager1.Modem' in v]
assert len(paths) == 1
props = dbus.Interface(bus.get_object('org.freedesktop.ModemManager1', paths[0]), 'org.freedesktop.DBus.Properties')
loc = props.GetAll('org.freedesktop.ModemManager1.Modem.Location')
assert int(loc['Enabled']) == 0 and not loc['SignalsLocation'] and int(loc['GpsRefreshRate']) == 30
blue = dbus.Interface(bus.get_object('org.bluez', '/'), 'org.freedesktop.DBus.ObjectManager').GetManagedObjects()
assert not any(v.get('org.bluez.Device1', {}).get('Connected', False) for v in blue.values())
adapters = [v['org.bluez.Adapter1'] for v in blue.values() if 'org.bluez.Adapter1' in v]
assert len(adapters) == 1 and not adapters[0]['Powered'] and not adapters[0]['Discovering']
bus.close()
watch = json.loads((root / 'gnss-assist/watch-state.json').read_text())
assert watch['running'] and not watch['active'] and watch['worker_starts'] == watch['worker_completions'] == 0
assert Path('/sys/module/imx471/parameters/unprocessed_fullres').read_text().strip() == 'N'
for path in ['/sys/bus/i2c/devices/7-0010', '/sys/bus/platform/devices/acb3000.camss', '/sys/bus/platform/devices/ac4b000.cci']:
    assert Path(path, 'power/runtime_status').read_text().strip() == 'suspended'
ssc = json.loads(Path('/run/samurai-ssc/state.json').read_text())
assert ssc['started']
(out / 'ssc-state-private.json').write_text(json.dumps(ssc, indent=2) + '\n')
remote = {(p / 'name').read_text().strip(): (p / 'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')}
assert remote == dict(adsp='running', slpi='running', modem='running')
log = subprocess.check_output(['dmesg'])
(out / 'dmesg-private.txt').write_bytes(log)
faults = {k: log.count(v) for k, v in dict(warning=b'WARNING:', oops=b'Oops:', gpu=b'gpu fault:', slpi_fatal=b'fatal error received', bluetooth=b'Frame reassembly failed').items()}
assert not any(faults.values()) and boot == Path('/proc/sys/kernel/random/boot_id').read_bytes()
report = dict(stage=233, current_identity_verified=True, same230_boot=True, kernel_build=183,
              running_intree2abde_note_verified=True,default_intree2abde_note_saved=True, module_files=len(modules), module_ko_count=772,
              camera_r13_r8_preserved=True, boot219_logdump183_persist_exact=True, nv_unchanged=True,
              remoteprocs=remote, faults=faults, taint=0, gps_idle=True, bt_off=True,
              no_module_service_power_change=True, no_transition_sent=True)

mfd=module_root/'kernel/drivers/mfd/qcom-pm8008.ko'
assert sha(mfd)=='d1ff82c022577e65b8d5cf8d98e56ea4170eb5bf4138516be843736db25a9dea'
assert not (module_root/'kernel/drivers/reset/reset-realme-rmx1931-pm8008.ko').exists()
assert not Path('/sys/module/reset_realme_rmx1931_pm8008').exists()
loaded_mfd=Path('/sys/module/qcom_pm8008/notes/.note.gnu.build-id').read_bytes()
assert loaded_mfd==note(mfd.read_bytes())
(out/'mfd-original-private.ko').write_bytes(mfd.read_bytes())
(out/'mfd-loaded-note-private.bin').write_bytes(loaded_mfd)
metadata={}
for n in modules:
 if n.endswith('.ko'):continue
 src=module_root/n;dest=out/'module-metadata-before'/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(src.read_bytes())
 st=src.stat();metadata[n]=dict(mode=st.st_mode & 0o777,uid=st.st_uid,gid=st.st_gid)
(out/'module-metadata-meta-private.json').write_text(json.dumps(metadata,indent=2)+'\n')
config=Path('/etc/modprobe.d/samurai-pmic-bringup.conf');assert not config.exists()
configs={}
for directory in ['/etc/modprobe.d','/run/modprobe.d','/usr/lib/modprobe.d','/lib/modprobe.d']:
 for f in Path(directory).glob('*.conf'):
  if f.is_file():
   data=f.read_bytes();configs[str(f)]=hashlib.sha256(data).hexdigest()
   assert not any('qcom_pm8008' in l.replace('-','_') or 'reset_realme_rmx1931_pm8008' in l.replace('-','_') for l in data.decode(errors='replace').splitlines() if not l.lstrip().startswith('#'))
(out/'loader-config-before-private.json').write_text(json.dumps(configs,indent=2)+'\n')
q=[n for n in Path('/sys/bus/i2c/devices').glob('*-0004') if (n/'driver').exists() and (n/'driver').resolve().name=='pm8008'];assert len(q)==1
(out/'pmic-q-before-private.json').write_text(json.dumps(dict(device=q[0].name,children=sorted(n.name for n in q[0].iterdir() if n.name.startswith('pm8008-'))),indent=2)+'\n')
report.update(old_mfd_default_and_loaded_note_match=True,old_mfd_backed_up=True,module_metadata_backed_up=len(metadata),loader_config_target_absent=True,old_q_bound=True)

(out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
