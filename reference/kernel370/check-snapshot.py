"""Compile the actual temporary diagnostic reader with ownership/bounds faults."""
from pathlib import Path
import json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;work=P/'snapshot-regression';work.mkdir(exist_ok=True)
s=(P/'camss-icp-a5-boot-test.c.proposed').read_text();a=s.index('static ssize_t firmware_read(');b=s.index('static const struct bin_attribute firmware_attribute',a)
(work/'body.inc').write_text(s[a:b]);(work/'probe.c').write_text((HERE/'snapshot-regression.c').read_text())
q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=address,undefined',str(work/'probe.c'),'-o',str(work/'probe')],capture_output=True)
assert not q.returncode,q.stderr.decode();rows=[]
for case in range(15):
 q=subprocess.run([str(work/'probe'),str(case)],capture_output=True,timeout=10)
 (work/(str(case)+'-private.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,(case,q.stderr.decode())
 rows.append(dict(case=case,passed=True))
report=dict(stage=370,verbatim_diagnostic_reader=True,asan_ubsan=True,mutex_and_dma_barrier_providers_mocked=True,
 tests=rows,requires_held_failed_start_and_matching_owner=True,requires_cpu_and_irq_off_reset_asserted=True,
 requires_power_reference_and_complete_firmware_mapping=True,negative_large_end_and_zero_length_bounds_checked=True,
 unavailable_after_cleanup=True,hardware_ram_cache_or_reset_integrity_not_proven=True,phone_operations=False,passed=True)
(HERE/'snapshot-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
