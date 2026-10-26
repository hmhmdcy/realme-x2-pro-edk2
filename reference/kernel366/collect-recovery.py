"""Read the newly reachable system without replaying the old A5 transaction."""
from pathlib import Path
import base64,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('strict184',HERE.parent/'kernel184/host.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
selected=json.loads((P.parent/'kernel303/fresh-working-endpoint-private.json').read_text());assert selected['kind']=='wifi'
s=(HERE.parent/'kernel360/recovery-inventory-device.py').read_text().replace('k298+','k363+').replace('k356-boot-r5','k366-boot-r1').replace('k305-geometry-r2','k366-work').replace("'/var/lib/samurai/k356-recovered/boot-id-private.txt'","'/var/lib/samurai/k365-work/boot-id-private.txt'")
s='\n'.join(line for line in s.splitlines() if not line.startswith("assert boot=="))
q=subprocess.run([base.SSH,'-T',*base.OPTIONS,'-4','-o','HostKeyAlias=169.254.42.1','root@'+selected['IPAddress'],'python3 -'],input=s.encode(),capture_output=True,timeout=30)
(P/'recovered-inventory-transport-private.log').write_bytes(q.stderr);q.check_returncode();d=json.loads(q.stdout);(P/'recovered-inventory-private.json').write_bytes(q.stdout)
for name,value in d['pstore_b64'].items():(P/('recovered-'+name+'-private')).write_bytes(base64.b64decode(value))
(P/'recovered-dmesg-private.txt').write_bytes(base64.b64decode(d['current_dmesg_b64']))
report=dict(stage=366,authenticated_via_original_key_wifi=True,new_boot_observed=not d['old_guard_matches']['/var/lib/samurai/k366-work/boot-id-private.txt'],
    kernel=d['kernel'],cpu_online=d['cpu_online'],taint=int(d['taint']),pstore_files=len(d['pstore_b64']),
    old_experiment_phase=d['r5_state']['phase'],old_experiment_terminal=d['r5_state']['terminal'],
    old_worker_pids=d['worker_pids'],icp_modules=d['modules'],temporary_dt_nodes=d['temporary_dt_nodes'],
    temporary_firmware_present=d['temporary_firmware_present'],clocks=d['icp_bps_ipe_clock_refs'],
    firmware_cpu_started_before_reset_unknown=True,firmware_boot_verified=False,explicit_system_reset_sent=False)
(HERE/'recovered-boot-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
