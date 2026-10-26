from pathlib import Path
import configparser,dbus,json,os,subprocess,time,traceback

os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k205-uart-reprobe-r2';assert not out.exists();out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k205-baseline/boot-id-private.txt').read_bytes()
candidate=root/'k205-tools/hci_uart-k205-diagnostic-r2-private.ko';original=Path('/usr/lib/modules')/os.uname().release/'kernel/drivers/bluetooth/hci_uart.ko'
trace=Path('/sys/kernel/tracing/instances/k205-uart-r2');assert not trace.exists();trace.mkdir()
events=['geni_serial_rx_data','geni_serial_tx_data','geni_serial_clk_cfg','geni_serial_set_termios','geni_serial_set_mctrl','geni_serial_get_mctrl']
for name in events:
 e=trace/'events/qcom_geni_serial'/name;(e/'filter').write_text('name == "c8c000.serial"');(e/'enable').write_text('1')
(trace/'buffer_size_kb').write_text('512');(trace/'trace_clock').write_text('mono')
before=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(before)
report=dict(stage=205,reprobe_cycles=[],bounded_trace_filtered_to_bluetooth_uart=True,payload_capture_observed=False);failure=None
def cmd(args,label,timeout=35):
 p=subprocess.run(args,capture_output=True,timeout=timeout);(out/(label+'-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0,label
try:
 for cycle in range(1,5):
  (trace/'trace').write_text('');(trace/'tracing_on').write_text('1');begin=time.monotonic()
  cmd(['rc-service','bluetooth','stop'],str(cycle)+'-bluez-stop');cmd(['/usr/sbin/samurai-bluetooth','stop'],str(cycle)+'-module-stop')
  for name in ['btbcm','btqca']:cmd(['insmod',str(original.parent/(name+'.ko'))],str(cycle)+'-'+name)
  cmd(['insmod',str(candidate),'samurai_rx_diag=1'],str(cycle)+'-candidate-load');cmd(['/usr/sbin/samurai-bluetooth','start'],str(cycle)+'-address');cmd(['rc-service','bluetooth','start'],str(cycle)+'-bluez-start')
  bus=dbus.SystemBus(private=True);obj=bus.get_object('org.bluez','/org/bluez/hci0');ap=dbus.Interface(obj,'org.freedesktop.DBus.Properties');manager=dbus.Interface(bus.get_object('org.bluez','/'),'org.freedesktop.DBus.ObjectManager')
  assert not ap.Get('org.bluez.Adapter1','Powered') and not ap.Get('org.bluez.Adapter1','Discovering');assert not any(v.get('org.bluez.Device1',{}).get('Connected',False) for v in manager.GetManagedObjects().values())
  for name in ['Pairable','Connectable']:ap.Set('org.bluez.Adapter1',name,dbus.Boolean(False,variant_level=1),timeout=10)
  ap.Set('org.bluez.Adapter1','Powered',dbus.Boolean(True,variant_level=1),timeout=20);assert ap.Get('org.bluez.Adapter1','Powered')
  for name in ['Pairable','Connectable','Discoverable']:ap.Set('org.bluez.Adapter1',name,dbus.Boolean(False,variant_level=1),timeout=10)
  time.sleep(.3);ap.Set('org.bluez.Adapter1','Powered',dbus.Boolean(False,variant_level=1),timeout=15);bus.close();time.sleep(.3)
  (trace/'tracing_on').write_text('0');(out/(str(cycle)+'-uart-trace-private.txt')).write_text((trace/'trace').read_text())
  stats={p.parent.name:p.read_text() for p in (trace/'per_cpu').glob('cpu*/stats')};(out/(str(cycle)+'-trace-stats-private.json')).write_text(json.dumps(stats,indent=2)+'\n')
  log=subprocess.check_output(['dmesg']);(out/(str(cycle)+'-dmesg-private.txt')).write_bytes(log);captured=log.count(b'RXDIAG head=')-before.count(b'RXDIAG head=')
  report['reprobe_cycles'].append(dict(cycle=cycle,elapsed_seconds=time.monotonic()-begin,baud_error_chunks_captured=captured,reassembly_delta_total=log.count(b'Frame reassembly failed')-before.count(b'Frame reassembly failed')));report['payload_capture_observed']=captured>0;(out/'progress.json').write_text(json.dumps(report,indent=2)+'\n')
  if captured:break
except Exception:
 failure=traceback.format_exc();(out/'failure-private.txt').write_text(failure)
finally:
 (trace/'tracing_on').write_text('0');(out/'final-uart-trace-private.txt').write_text((trace/'trace').read_text())
 for name in events:(trace/'events/qcom_geni_serial'/name/'enable').write_text('0')
 trace.rmdir();after=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(after);report['failed']=failure is not None;report['fault_delta']={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',reassembly=b'Frame reassembly failed').items()};report['taint']=int(Path('/proc/sys/kernel/tainted').read_text());report['trace_instance_removed']=not trace.exists();(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
