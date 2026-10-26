"""Bounded, per-boot private UART capture around the normal Bluetooth startup."""
from pathlib import Path
import json,os,subprocess,sys,time

os.umask(0o077);root=Path('/var/lib/samurai');boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();out=root/'k205-boottrace'/boot
instance=Path('/sys/kernel/tracing/instances/k205-bt-boot');events=['geni_serial_rx_data','geni_serial_tx_data','geni_serial_clk_cfg','geni_serial_set_termios','geni_serial_set_mctrl','geni_serial_get_mctrl']
assert sys.argv[1:] in [['start'],['finish']]
if sys.argv[1]=='start':
 assert boot!=(root/'k205-baseline/boot-id-private.txt').read_text().strip()
 if out.exists():
  assert (out/'boot-id-private.txt').read_text().strip()==boot
  print('Current boot UART capture already requested; no duplicate worker.')
  raise SystemExit(0)
 out.mkdir(mode=0o700,parents=True);(out/'boot-id-private.txt').write_text(boot+'\n');assert not instance.exists();instance.mkdir()
 (instance/'buffer_size_kb').write_text('2048');(instance/'trace_clock').write_text('mono')
 for name in events:
  e=instance/'events/qcom_geni_serial'/name;(e/'filter').write_text('name == "c8c000.serial"');(e/'enable').write_text('1')
 (instance/'tracing_on').write_text('1')
 with (out/'worker-private.log').open('xb') as log:
  p=subprocess.Popen(['/usr/bin/python3',__file__,'finish'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 (out/'worker-pid-private.txt').write_text(str(p.pid)+'\n');print('Private UART boot capture armed.')
else:
 assert out.is_dir() and instance.is_dir();time.sleep(40)
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==boot
 (instance/'tracing_on').write_text('0');(out/'uart-trace-private.txt').write_text((instance/'trace').read_text())
 stats={p.parent.name:p.read_text() for p in (instance/'per_cpu').glob('cpu*/stats')};(out/'trace-stats-private.json').write_text(json.dumps(stats,indent=2)+'\n')
 for name in events:(instance/'events/qcom_geni_serial'/name/'enable').write_text('0')
 instance.rmdir();(out/'summary.json').write_text(json.dumps(dict(stage=205,finite_40_second_capture_completed=True,trace_instance_removed=True,source='normal startup no forced discovery'),indent=2)+'\n')
