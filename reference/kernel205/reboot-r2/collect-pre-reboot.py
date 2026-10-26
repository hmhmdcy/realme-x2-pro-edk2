from pathlib import Path
import dbus,hashlib,json,os,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k205r2-before-reboot'
if out.exists():
 assert not (out/'summary.json').exists() and (out/'boot-id-private.txt').read_bytes()==Path('/proc/sys/kernel/random/boot_id').read_bytes()
else:out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k205-runtime/boot-id-private.txt').read_bytes();(out/'boot-id-private.txt').write_bytes(boot)
assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert Path('/sys/firmware/devicetree/base/model').read_bytes()==b'Realme X2 Pro (RMX1931CN)\0'
(out/'start-uptime-private.txt').write_text(Path('/proc/uptime').read_text())
hashes={}
expected_persist=json.loads((root/'k200-runtime/partition-hashes-private.json').read_text())['persist']
for dev,label,size,digest in [('sde11','boot',100663296,'cdd16e29f3639dd79fe7c1a98ac3a5fcb2827d701d2291af93a4da0884476082'),('sde32','logdump',67108864,'e73754c7d327925acf031aed54e0e6d02069b7a112c32b187ac9bfb468da1358'),('sda2','persist',None,expected_persist)]:
 path='/dev/'+dev;assert subprocess.check_output(['lsblk','-ndo','PARTLABEL',path],text=True).strip()==label
 if size:assert int(subprocess.check_output(['blockdev','--getsize64',path],text=True))==size
 value=subprocess.check_output(['sha256sum',path],text=True).split()[0];assert value==digest,label;hashes[path]=value
(out/'partition-check.sha256').write_text(''.join(value+'  '+name+'\n' for name,value in hashes.items()))
subprocess.run(['sha256sum','-c','/run/samurai-wifi/nv-source-hashes.txt'],check=True,stdout=(out/'nv-check-private.txt').open('wb'))
tree=(root/'k205-bootdiag-deploy/paired-module-tree.sha256').read_bytes();(out/'module-tree.sha256').write_bytes(tree)
subprocess.run(['sha256sum','-c',str(out/'module-tree.sha256')],cwd=Path('/usr/lib/modules')/os.uname().release,check=True,stdout=(out/'module-tree-check-private.txt').open('wb'))
assert len(tree.splitlines())==784
expected={'/usr/sbin/samurai-bluetooth':'ae46b800ed036f0527c6a0434c7da03c8a722abf74a34b420cbe44e1913ef762','/usr/sbin/samurai-ssc':'9a1fd03f5f8e6f1b893f75465b01d1097419b06d41eaa24438aa1b63ee2f287c','/usr/bin/ModemManager':'b350c55ba334b7d23564136fe3ce19bf37f95db0d374f63cc89351341d9b9ddc','/usr/sbin/samurai-gnss-assist':'42168f33472d01dbf115ea766487c70d95332aabc8de02c25bdb381cea80af97','/etc/init.d/samurai-gnss-assist':'54b8174507e97badfafba6c373ebf937045c1c85034f094e7de910369af78af3'}
assert all(hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest for name,digest in expected.items())
(out/'userspace-check.sha256').write_text(''.join(digest+'  '+name+'\n' for name,digest in expected.items()))
bus=dbus.SystemBus(private=True);mp=dbus.Interface(bus.get_object('org.freedesktop.ModemManager1','/org/freedesktop/ModemManager1/Modem/0'),'org.freedesktop.DBus.Properties');loc=mp.GetAll('org.freedesktop.ModemManager1.Modem.Location');m=mp.GetAll('org.freedesktop.ModemManager1.Modem');assert int(loc['Enabled'])==0 and not loc['SignalsLocation'] and int(loc['GpsRefreshRate'])==30 and int(m['PowerState'])==1
assert not bus.name_has_owner('org.freedesktop.GeoClue2');bus.close()
watch=json.loads((root/'gnss-assist/watch-state.json').read_text());assert watch['running'] and not watch['active'] and watch['worker_starts']==watch['worker_completions']==0
assert watch['time_prepared'] and watch['time_preparation_starts']==watch['time_preparation_completions']>=1
assert watch['source_sha256']==expected['/usr/sbin/samurai-gnss-assist']
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')};assert all(v=='running' for v in rp.values())
assert json.loads(Path('/run/samurai-ssc/state.json').read_text())['started']
assert Path('/sys/firmware/devicetree/base/soc@0/camss@acb3000/power-domain-names').read_bytes()==b'ife0\0ife1\0top\0mmcx\0'
assert all(not Path('/sys/module/'+n).exists() for n in ['samurai_front_overlay','samurai_vio_phandle','samurai_cci_bringup','imx471','qcom_pm8008','i2c_qcom_cci'])
log=subprocess.check_output(['dmesg']);(out/'dmesg-private.txt').write_bytes(log);counts={k:log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()};assert counts==dict(warning=0,oops=0,gpu=0,slpi_fatal=0,bluetooth=0)
r=dict(stage=205,fresh_current_identity_verified=True,same_boot205_first_cycle=True,kernel_build=183,taint=0,uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]),boot204_logdump183_and_persist_readback_exact=True,module_tree_784_files_exact=True,gnss_assist_source_and_init_exact=True,gps_enabled=0,mm_power_state=int(m['PowerState']),assist_idle=True,remoteprocs=rp,fault_counts=counts,no_transition_sent=True)
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
