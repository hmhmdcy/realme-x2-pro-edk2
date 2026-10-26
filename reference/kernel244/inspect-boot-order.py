from pathlib import Path
import dbus,hashlib,json,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
scripts={p.name:p.read_text() for p in Path('/etc/init.d').glob('samurai*') if p.is_file() and p.stat().st_size<256*1024}
runlevels={p.name:[x.name for x in p.iterdir()] for p in Path('/etc/runlevels').iterdir() if p.is_dir()}
requested=next(p for p in Path('/sys/class/remoteproc').glob('*') if (p/'name').read_text().strip()=='modem');param=Path('/sys/module/firmware_class/parameters/path').read_text().strip();base=(Path(param)/(requested/'firmware').read_text().strip()).parent
expected={line.split()[1]:line.split()[0] for line in Path('/etc/samurai-wifi/modem-sha256.txt').read_text().splitlines()};checks={name:hashlib.sha256((base/name).read_bytes()).hexdigest()==digest for name,digest in expected.items()}
report=dict(stage=244,same236_boot=True,kernel_release=subprocess.check_output(['uname','-r']).decode().strip(),modem_firmware_files=len(checks),all_modem_firmware_hashes_match=all(checks.values()),boot_script_names=list(scripts),default_services=runlevels.get('default'),root_filesystem=next(line.split()[2] for line in Path('/proc/mounts').read_text().splitlines() if line.split()[1]=='/'))
print(json.dumps({'report':report,'private':{'scripts':scripts,'runlevels':runlevels,'rc_status':subprocess.run(['rc-status','-a'],capture_output=True).stdout.decode(),'model':Path('/proc/device-tree/model').read_bytes().rstrip(b'\0').decode(),'compatible':Path('/proc/device-tree/compatible').read_bytes().decode(errors='replace'),'cmdline':Path('/proc/cmdline').read_text()}}))
