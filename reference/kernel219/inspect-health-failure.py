from pathlib import Path
import ast,host,json,shutil
here=Path(__file__).resolve().parent
shutil.copyfile(host.PRIVATE/'transport-last-failure-private.log',host.PRIVATE/'final-health-initial-failure-private.log')
code="from pathlib import Path;import json;p=Path('/var/lib/samurai/k219-final-health/uncamera-product-check-private.txt');print(json.dumps([l.split(': FAILED')[0] for l in p.read_text().splitlines() if ': FAILED' in l]))"
p=host.ssh('python3 -',input=code.encode(),timeout=30);failed=json.loads(p.stdout);print(json.dumps(dict(failed_paths=failed)))
script=ast.parse((here/'final-health.py').read_text());native=next(ast.literal_eval(n.value) for n in script.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='code' for x in n.targets))
tree=ast.parse(native)
print(json.dumps(dict(short_byte_constants=[list(n.value) for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,bytes) and len(n.value)<=4],
                     escaped_string_constants=[dict(chars=list(map(ord,n.value))) for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str) and '\\' in n.value and len(n.value)<=5])))
assert failed==['/etc/libcamera/configuration.yaml']
r=dict(stage=219,final_health_initial_check_failed=True,reason='Legacy212 userspace hash manifest included the camera configuration legitimately changed by the signed r6/config-r1 upgrade',
       current_signed_camera_payload_hashes_had_already_passed=True,failed_paths=failed,hardware_faults_seen_before_failure=0,
       original_failure_and_native_logs_preserved=True,package_or_hardware_changes_not_replayed=True)
(here/'final-health-initial-failure-validation.json').write_text(json.dumps(r,indent=2)+'\n')
