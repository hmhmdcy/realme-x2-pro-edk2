from pathlib import Path
import json,shlex
import host
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel369/poll-boot.py').read_text().replace('k369-boot-','k371-boot-').replace('stage=369','stage=371').replace("'dump-collector.py'","'snapshot-collector.py'")
s=s.replace("or path.name.startswith('a5-devcd') and path.suffix=='.bin'","or path.name.startswith('a5-devcd') and path.suffix=='.bin' or path.name.startswith('firmware-') or path.name=='snapshot-result-private.json'")
s=s.replace("keys=['terminal'","keys=['held_window_returned','snapshot_saved','code_page_match','cleanup_attempted','terminal'")
compile(s,'poll-boot.py','exec');(HERE/'poll-boot.py').write_text(s)
code='''from pathlib import Path
import json
print(json.dumps(dict(taint=int(Path('/proc/sys/kernel/tainted').read_text()),release=Path('/proc/sys/kernel/osrelease').read_text().strip(),
 transaction_absent=not Path('/var/lib/samurai/k371-boot-r1').exists(),core_absent=not Path('/sys/module/qcom_camss_icp_a5_core').exists(),
 test_absent=not Path('/sys/module/camss_icp_a5_boot_test').exists(),firmware_absent=not Path('/lib/firmware/qcom/sm8150/samurai-icp356.elf').exists(),
 camss=Path('/sys/bus/platform/devices/acb3000.camss/power/runtime_status').read_text().strip())))
'''
q=host.ssh('python3 -c '+shlex.quote(code),timeout=20);d=json.loads(q.stdout)
assert d['taint']==0 and d['transaction_absent'] and d['core_absent'] and d['test_absent'] and d['firmware_absent'] and d['camss']=='suspended'
report=dict(stage=371,current369_guard_verified=True,**d,passed=True)
(HERE/'preflight-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
