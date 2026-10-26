from pathlib import Path
import dbus,hashlib,json,os,struct,subprocess,time,traceback

os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k205-diagnostic-load';assert not out.exists();out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k205-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
candidate=root/'k205-tools/hci_uart-k205-diagnostic-r2-private.ko';build=json.loads((root/'k205-tools/diagnostic-build-validation.json').read_text());assert hashlib.sha256(candidate.read_bytes()).hexdigest()==build['candidate_sha256']
original=Path('/usr/lib/modules')/os.uname().release/'kernel/drivers/bluetooth/hci_uart.ko';assert hashlib.sha256(original.read_bytes()).hexdigest()=='f6c5ed3538270480a72cf4bf8b1339103417941930b0d8ecb941fd11d16d7020'
bus=dbus.SystemBus(private=True);objects=dbus.Interface(bus.get_object('org.bluez','/'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects();assert not any(v.get('org.bluez.Device1',{}).get('Connected',False) for v in objects.values());adapters=[v['org.bluez.Adapter1'] for v in objects.values() if 'org.bluez.Adapter1' in v];assert len(adapters)==1 and not adapters[0]['Powered'] and not adapters[0]['Discovering'];bus.close()
before=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(before)
def command(args,label,timeout=35):
 p=subprocess.run(args,capture_output=True,timeout=timeout);(out/(label+'-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0,label
stopped=False
try:
 command(['rc-service','bluetooth','stop'],'bluez-stop');command(['/usr/sbin/samurai-bluetooth','stop'],'modules-stop');stopped=True
 assert not Path('/sys/class/bluetooth/hci0').exists()
 for n in ['btbcm','btqca']:command(['insmod',str(original.parent/(n+'.ko'))],n+'-load')
 command(['insmod',str(candidate),'samurai_rx_diag=1'],'candidate-load')
 command(['/usr/sbin/samurai-bluetooth','start'],'address-provision-and-lifecycle')
 command(['rc-service','bluetooth','start'],'bluez-start')
 assert Path('/sys/module/hci_uart/parameters/samurai_rx_diag').read_text().strip()=='Y'
 data=candidate.read_bytes();offset=struct.unpack_from('<Q',data,40)[0];size,count,index=struct.unpack_from('<HHH',data,58);headers=[struct.unpack_from('<IIQQQQIIQQ',data,offset+i*size) for i in range(count)];strings=data[headers[index][4]:headers[index][4]+headers[index][5]];notes=[r for r in headers if strings[r[0]:].split(b'\0',1)[0]==b'.note.gnu.build-id'];assert len(notes)==1;note=notes[0];assert Path('/sys/module/hci_uart/notes/.note.gnu.build-id').read_bytes()==data[note[4]:note[4]+note[5]]
 after=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(after);delta={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',reassembly=b'Frame reassembly failed',qca_setup=b'QCA Failed',slpi_fatal=b'fatal error received').items()};assert all(v==0 for k,v in delta.items() if k!='reassembly') and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 report=dict(stage=205,temporary_diagnostic_loaded=True,loaded_build_id_matches_candidate=True,installed185_module_unchanged=True,diagnostic_enabled=True,fault_delta=delta,baud_error_payloads_captured=after.count(b'RXDIAG head=')-before.count(b'RXDIAG head='),no_reboot_or_partition_flash=True)
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
except Exception:
 (out/'failure-private.txt').write_text(traceback.format_exc())
 if stopped:
  for args,label in [(['rc-service','bluetooth','stop'],'rollback-bluez-stop'),(['/usr/sbin/samurai-bluetooth','stop'],'rollback-module-stop'),(['/usr/sbin/samurai-bluetooth','start'],'rollback-original-start'),(['rc-service','bluetooth','start'],'rollback-bluez-start')]:
   p=subprocess.run(args,capture_output=True,timeout=35);(out/(label+'-private.log')).write_bytes(p.stdout+p.stderr)
 raise
