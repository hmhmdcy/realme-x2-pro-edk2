from pathlib import Path
import importlib.util,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel241')
spec=importlib.util.spec_from_file_location('host241',R.parent/'kernel240/host.py')
host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
code=r'''
from pathlib import Path
import hashlib,json,re
r=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes()
source=next((r/'k190-mm-build/source').iterdir())/'src/mm-shared-qmi.c'
text=source.read_text();names=sorted(set(re.findall(r'\bqmi_client_loc_[a-z_]+(?=\s*\()',text)))
report=dict(stage=241,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
 daemon_sha256=hashlib.sha256(Path('/usr/bin/ModemManager').read_bytes()).hexdigest(),loc_calls=names,
 relevant_source_lines=[dict(line=i+1,text=line.strip()) for i,line in enumerate(text.splitlines()) if re.search(r'loc_(start|register_events|set_operation_mode|set_nmea_types|set_engine_lock|inject|set_gnss|register_master|platform_power)',line)],readonly=True)
print(json.dumps(report))
'''
result=host.ssh('python3 -',input=code.encode(),timeout=15)
(P/'linux-source-host-private.log').write_bytes(result.stdout+result.stderr)
report=json.loads(result.stdout)
(R/'linux-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
