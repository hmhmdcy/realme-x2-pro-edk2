import hashlib,json,os,subprocess,sys,time
from pathlib import Path
import dbus
sys.path.insert(0,'/tmp')
from k130_bt_mgmt import Management,snapshot
os.umask(0o077)
root=Path('/var/lib/samurai/k130-warmboot');root.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot!=Path('/var/lib/samurai/k130-quiesce/boot-id-private.txt').read_bytes()
assert subprocess.check_output(['uname','-v'],text=True).startswith('#129 ')
(root/'boot-id-private.txt').write_bytes(boot)
def save(name,v): (root/name).write_text(json.dumps(v,indent=2,default=str)+'\n')
def capture(name,args,timeout=30):
 with (root/name).open('xb') as f: subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=timeout)
end=time.monotonic()+150;bus=dbus.SystemBus(private=True)
while time.monotonic()<end:
 ready=bus.name_has_owner('org.bluez') and subprocess.run(['pgrep','-x','phosh'],stdout=subprocess.DEVNULL).returncode==0 and subprocess.run(['pgrep','-x','phoc'],stdout=subprocess.DEVNULL).returncode==0
 if ready: break
 time.sleep(2)
assert ready,'automatic service/desktop readiness bound expired'
assert 'status: started' in subprocess.check_output(['rc-service','bluetooth','status'],text=True)
capture('dmesg-before.txt',['dmesg'])
query=Path('/run/samurai-radio-address/current-bt').read_text().strip();assert Path(query,'boot-id').read_bytes()==boot
address=Path(query,'bt-mac-le.bin').read_bytes();assert len(address)==6
assert Path(query,'bt-mac-le.bin').stat().st_mode & 0o777==0o600
capture('radio-cache-status.txt',['/usr/bin/samurai-radio-address','status'])
capture('service-status.txt',['rc-service','bluetooth','status'])
(root/'startup-address-private.txt').write_bytes(Path('/run/samurai-bluetooth-openrc.log').read_bytes())
assert b'RADIO_ADDRESS_QUERY_VERIFIED kind=bt' in (root/'startup-address-private.txt').read_bytes()
assert b'BT_ADDRESS_VERIFIED index=0 powered=0 connectable=0 bondable=0' in (root/'startup-address-private.txt').read_bytes()
capture('startup-radio.txt',['cat','/run/samurai-wifi/boot-finished'])
assert (root/'startup-radio.txt').read_bytes()==b'0\n'
props=dbus.Interface(bus.get_object('org.bluez','/org/bluez/hci0'),'org.freedesktop.DBus.Properties')
mgmt=Management(root/'mgmt-private.jsonl')
initial=snapshot(mgmt);save('mgmt-initial-private.json',initial)
assert initial['configured']==[0] and not initial['unconfigured'] and initial['info']['address_le']==address.hex() and not initial['info']['settings'] & 1
samples=[];ids={n:subprocess.check_output(['pgrep','-x',n],text=True).strip() for n in ['phosh','phoc']}
for i in range(6):
 p=dict(props.GetAll('org.bluez.Adapter1',timeout=10));save(f'adapter-{i}-private.json',p)
 assert p['Address'].lower()==':'.join(f'{x:02x}' for x in address[::-1])
 assert not p['Powered'] and not p['Discovering']
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 for name,pid in ids.items():assert subprocess.check_output(['pgrep','-x',name],text=True).strip()==pid
 capture(f'wifi-link-{i}-private.txt',['iw','dev','wlan0','link'])
 assert b'freq: 5180' in (root/f'wifi-link-{i}-private.txt').read_bytes()
 for index in [1,2]:assert Path(f'/sys/class/remoteproc/remoteproc{index}/state').read_text().strip()=='running'
 samples.append(dict(sample=i,monotonic=time.monotonic(),frequency_mhz=5180,taint=0,bluetooth_service_running=True,controller_powered=False,discovering=False,same_gui=True,radio_audio_running=True))
 if i<5:time.sleep(10)
save('samples.json',samples)
final=snapshot(mgmt);save('mgmt-final-private.json',final);mgmt.close();bus.close()
assert final['info']['address_le']==address.hex() and not final['info']['settings'] & 1
import shutil
shutil.copytree('/run/samurai-radio-address',root/'radio-address-private',symlinks=True)
(root/'wifi-profile-private.nmconnection').write_bytes(Path('/etc/NetworkManager/system-connections/samurai-wifi.nmconnection').read_bytes())
capture('default-service.txt',['readlink','/etc/runlevels/default/bluetooth'])
(root/'bluetooth-service').write_bytes(Path('/etc/init.d/bluetooth').read_bytes())
(root/'main.conf-private').write_bytes(Path('/etc/bluetooth/main.conf').read_bytes())
capture('nv-check.txt',['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'])
capture('source-check.txt',['sha256sum','-c','/var/lib/samurai/k111-sensor-sources-readonly/sources-before.sha256'])
capture('vendor-check.txt',['sha256sum','-c','/var/lib/samurai/k115-vendor-camera-source/vendor-before.sha256'])
with (root/'module-check.txt').open('xb') as f:
 subprocess.run(['sha256sum','-c','/var/lib/samurai/k129-preflash/new-module-tree.sha256'],cwd='/usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k129+',stdout=f,stderr=subprocess.STDOUT,check=True,timeout=45)
capture('partitions.sha256',['sha256sum','/dev/sde11','/dev/sde32','/dev/sda2'],timeout=60)
gateway=subprocess.check_output(['ip','route','show','default','dev','wlan0'],text=True).split()[2]
capture('gateway-private.txt',['ping','-I','wlan0','-c','3','-W','3',gateway])
capture('https-result.txt',['curl','--interface','wlan0','--fail','--max-time','20','-sS','-o',str(root/'https-body.txt'),'-w','%{http_code} %{size_download}\n','https://example.com'])
capture('taint.txt',['cat','/proc/sys/kernel/tainted'])
capture('drm-state.txt',['cat','/sys/kernel/debug/dri/1/state'])
capture('sensor.txt',['cat','/sys/class/remoteproc/remoteproc0/state','/sys/devices/platform/sensor-power/state'])
capture('pcm.txt',['cat','/proc/asound/card0/pcm0p/sub0/status','/proc/asound/card0/pcm1c/sub0/status'])
capture('amps.txt',['cat','/sys/bus/i2c/devices/1-0039/status','/sys/bus/i2c/devices/1-003a/status'])
capture('console-node.txt',['stat','-c','%F %a %t %T %u %g','/dev/console'])
capture('dmesg-after.txt',['dmesg'])
save('result.json',dict(new_warm_boot_same_kernel129=True,automatic_openrc_bluez_and_fresh_dms_address_ready=True,no_manual_service_activation_or_address_provision_after_reboot=True,software_reboot_not_physical_coldboot=True,controller_final_powered=False,discovery_final_off=True,service_running=True))
lines=[]
for p in sorted(root.rglob('*')):
 if p.is_file() and not p.is_symlink():lines.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  ./'+p.relative_to(root).as_posix())
(root/'SHA256SUMS').write_text('\n'.join(lines)+'\n')
subprocess.run(['tar','-C',str(root),'-czf','/tmp/k130-warmboot-private.tar.gz','.'],check=True,timeout=30)
archive=Path('/tmp/k130-warmboot-private.tar.gz')
Path(str(archive)+'.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+str(archive)+'\n')
print('K130_REAL_WARM_BOOT_AUTOMATIC_BLUEZ_DMS_5GHZ_SIX_SAMPLES_CAPTURED',flush=True)
