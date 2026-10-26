from pathlib import Path
import base64,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=(HERE.parent/'kernel360/recovery-inventory-device.py').read_text().replace('k298+','k363+').replace('k356-boot-r5','k369-boot-r1').replace('k305-geometry-r2','k367-work')
s='\n'.join(line for line in s.splitlines() if not line.startswith('assert boot=='))
q=host.raw_ssh('python3 -',input=s.encode(),timeout=30);(P/'recovered-inventory-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
for name,value in d['pstore_b64'].items():(P/('recovered-'+name+'-private')).write_bytes(base64.b64decode(value))
(P/'recovered-dmesg-private.txt').write_bytes(base64.b64decode(d['current_dmesg_b64']))
raw=P/'collected-r1/a5-devcd1-private.bin'
report=dict(stage=369,new_boot_observed=not d['old_guard_matches']['/var/lib/samurai/k367-work/boot-id-private.txt'],
    old_worker_pids=d['worker_pids'],kernel=d['kernel'],taint=int(d['taint']),cpu_online=d['cpu_online'],pstore_files=len(d['pstore_b64']),
    icp_modules=d['modules'],temporary_dt_nodes=d['temporary_dt_nodes'],clocks=d['icp_bps_ipe_clock_refs'],
    temporary_firmware_present=d['temporary_firmware_present'],old_transaction_terminal=d['r5_state']['terminal'],
    old_phase=d['r5_state']['phase'],collector_armed_before_boot_module=d['r5_state'].get('collector_armed_before_boot_module',False),
    bounded_raw_snapshot_recovered=raw.exists() and raw.stat().st_size==568,explicit_host_reset_sent=False,firmware_handshake_verified=False)
(HERE/'recovered-boot-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
