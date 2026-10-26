from pathlib import Path
import base64,json,re
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=(HERE.parent/'kernel360/recovery-inventory-device.py').read_text().replace('k298+','k363+').replace('k356-boot-r5','k371-boot-r1').replace('k305-geometry-r2','k369-recovered')
s='\n'.join(line for line in s.splitlines() if not line.startswith('assert boot=='))
q=host.raw_ssh('python3 -',input=s.encode(),timeout=30);(P/'recovered-inventory-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
for name,value in d['pstore_b64'].items():(P/('recovered-'+name+'-private')).write_bytes(base64.b64decode(value))
(P/'recovered-dmesg-private.txt').write_bytes(base64.b64decode(d['current_dmesg_b64']))
texts=[base64.b64decode(value).decode(errors='replace') for value in d['pstore_b64'].values()]
lines=[line for s in texts for line in s.splitlines() if 'A5 ' in line or 'Firmware memory resolves' in line]
(P/'a5-ramoops-excerpt-private.txt').write_text('\n'.join(lines)+'\n')
report=dict(stage=371,new_boot_observed=not d['old_guard_matches']['/var/lib/samurai/k369-recovered/boot-id-private.txt'],
 old_worker_pids=d['worker_pids'],kernel=d['kernel'],taint=int(d['taint']),cpu_online=d['cpu_online'],pstore_files=len(d['pstore_b64']),
 icp_modules=d['modules'],temporary_dt_nodes=d['temporary_dt_nodes'],clocks=d['icp_bps_ipe_clock_refs'],
 temporary_firmware_present=d['temporary_firmware_present'],old_transaction_terminal=d['r5_state']['terminal'],old_phase=d['r5_state']['phase'],
 collector_armed_before_boot_module=d['r5_state'].get('collector_armed_before_boot_module',False),
 actual_held_window_return_observed=False,host_reset_sent=False,
 ramoops_cpu_release=any('A5 CPU release' in line for line in lines),ramoops_reset_asserted=any('A5 stopped, block reset asserted' in line for line in lines),
 ramoops_dma_retirement_started=any('A5 retiring DMA aliases' in line for line in lines),ramoops_dma_retirement_completed=any('A5 DMA aliases retired' in line for line in lines),
 ramoops_pm_reference_release_observed=any('A5 PM reference released' in line for line in lines),
 captured_files=[p.name for p in (P/'collected-r1').iterdir()] if (P/'collected-r1').exists() else [],firmware_handshake_verified=False)
(HERE/'recovered-boot-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
