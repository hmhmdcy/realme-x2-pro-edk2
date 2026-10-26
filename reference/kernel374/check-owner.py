from pathlib import Path
import json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;work=P/'owner-regression';work.mkdir(exist_ok=True)
s=(P/'camss-icp-a5-boot-test.c.proposed').read_text();parts=[]
for start,end in [('static int group_device(','static void update_result('),('static int cleanup(void)','static ssize_t cleanup_store('),('static ssize_t run_store(','static DEVICE_ATTR_WO(run)'),('static int boot_test_probe(','static void boot_test_remove(')]:
 a=s.index(start);b=s.index(end,a);parts.append(s[a:b])
(work/'owner-bodies.inc').write_text('\n'.join(parts));prefix=(HERE/'owner-regression.c').read_text().replace('struct device {void *data;};','struct device {void *data;void *of_node;};')
(work/'probe.c').write_text(prefix)
q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-unused-function','-Wno-misleading-indentation','-fsanitize=address,undefined',str(work/'probe.c'),'-o',str(work/'probe')],capture_output=True);assert not q.returncode,q.stderr.decode()
rows=[]
for case in list(range(15))+[20,21,22,23]:
 q=subprocess.run([str(work/'probe'),str(case)],capture_output=True,timeout=10);(work/(str(case)+'-private.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,(case,q.stderr.decode())
 rows.append(dict(case=case,passed=True))
report=dict(stage=374,actual_probe_run_store_run_locked_and_cleanup_bodies=True,asan_ubsan=True,resource_pm_firmware_and_module_providers_mocked=True,
 tests=rows,probe_never_requests_or_starts_firmware=True,unbound_busy_or_wrong_owner_never_runs=True,
 transient_module_reference_balanced=True,failed_owned_backing_keeps_persistent_module_pin=True,repeated_fully_released_run_allowed=True,
 actual_platform_binding_and_hardware_handshake_not_proven=True,phone_operations=False,passed=True)
(HERE/'owner-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='tests'},indent=2))
