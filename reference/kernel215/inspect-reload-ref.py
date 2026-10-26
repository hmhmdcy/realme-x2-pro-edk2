from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import hashlib,json
root=Path('/var/lib/samurai');base=root/'k215-baseline'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(base/'boot-id-private.txt').read_bytes()
module=Path('/sys/module/imx471');p=Path('/usr/lib/modules')/__import__('os').uname().release/'kernel/drivers/media/i2c/imx471.ko'
record=dict(module_loaded=module.exists(),refcnt=(module/'refcnt').read_text().strip(),holders=[p.name for p in (module/'holders').iterdir()],proc_module_line=next(line for line in Path('/proc/modules').read_text().splitlines() if line.startswith('imx471 ')),driver=Path('/sys/bus/i2c/devices/7-0010/driver').resolve().name,module_file_matches_original=hashlib.sha256(p.read_bytes()).digest()==hashlib.sha256((base/'imx471-original.ko').read_bytes()).digest(),unbind_available=Path('/sys/bus/i2c/drivers/imx471/unbind').is_file(),taint=Path('/proc/sys/kernel/tainted').read_text().strip())
assert record['module_loaded'] and record['module_file_matches_original'] and record['driver']=='imx471' and record['taint']=='0'
marker=root/'k215-driver-test/transition-state-private.json';old=json.loads(marker.read_text());assert old['state']=='failed-restored';marker.write_text(json.dumps(dict(state='failed-no-driver-change',previous_label='failed-restored',corrected_after_authoritative_module_and_file_inspection=True))+'\n')
print(json.dumps(record))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=30);record=json.loads(p.stdout);(host.PRIVATE/'driver-ref-inspection-private.json').write_bytes(p.stdout)
public={key:value for key,value in record.items() if key!='proc_module_line'};(here/'reload-ref-validation.json').write_text(json.dumps(public,indent=2)+'\n');print(json.dumps(public))
