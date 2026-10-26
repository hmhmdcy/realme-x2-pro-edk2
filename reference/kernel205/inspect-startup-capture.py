from pathlib import Path
import json
import host

code=r'''
from pathlib import Path
import json,subprocess
root=Path('/var/lib/samurai');boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot==(root/'k205-runtime/boot-id-private.txt').read_text().strip()
out=root/'k205-boottrace'/boot;exists=out.exists();pid=int((out/'worker-pid-private.txt').read_text()) if (out/'worker-pid-private.txt').exists() else None
running=pid is not None and Path('/proc/%d'%pid).exists() and b'boot-uart-trace.py' in Path('/proc/%d/cmdline'%pid).read_bytes()
summary=(out/'summary.json').exists();trace=(out/'uart-trace-private.txt').exists();dmesg=subprocess.check_output(['dmesg']);(root/'k205-runtime/dmesg-startup-capture-private.txt').write_bytes(dmesg)
r=dict(stage=205,current_boot_capture_directory_exists=exists,capture_worker_running=running,capture_summary_present=summary,trace_present=trace,reassembly_count=dmesg.count(b'Frame reassembly failed'),diagnostic_error_chunk_count=dmesg.count(b'RXDIAG head='))
if summary:
 assert not running;record=json.loads((out/'summary.json').read_text());assert record['finite_40_second_capture_completed']
 stats=json.loads((out/'trace-stats-private.json').read_text());r['all_cpu_trace_overrun_zero']=all('overrun: 0' in v and 'commit overrun: 0' in v for v in stats.values())
 (root/'k205-runtime/startup-capture-private.json').write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps(r));print(str(out))
else:print(json.dumps(r))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=20);lines=p.stdout.decode().splitlines();report=json.loads(lines[0]);(host.PRIVATE/'startup-capture-observation-private.json').write_text(json.dumps(report,indent=2)+'\n')
if report['capture_summary_present']:
 remote=lines[1];assert remote.startswith('/var/lib/samurai/k205-boottrace/')
 for name in ['uart-trace-private.txt','trace-stats-private.json','worker-private.log']:host.download(remote+'/'+name,host.PRIVATE/('boot-'+name))
 host.download('/var/lib/samurai/k205-runtime/dmesg-startup-capture-private.txt',host.PRIVATE/'boot-dmesg-private.txt')
 (Path(__file__).resolve().parent/'startup-capture-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
