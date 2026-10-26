from pathlib import Path
import base64,hashlib,json,re
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
observed=json.loads((P/'observation-r1-private.json').read_text());inventory=json.loads((P/'recovered-inventory-private.json').read_text())
state=observed['state'];assert not observed['same_boot'] and not observed['worker_live'] and not observed['collector_live'] and not state['terminal']
manifest=json.loads(inventory['r5_manifest']);assert manifest['payload_sha256']['worker.py']==hashlib.sha256((HERE/'boot-worker.py').read_bytes()).hexdigest()
assert "'hold_start_failure=1'" in (HERE/'boot-worker.py').read_text()
lines=(P/'a5-ramoops-excerpt-private.txt').read_text().splitlines();release=next(line for line in lines if 'A5 CPU release' in line);response=next(line for line in lines if 'A5 HFI response=' in line)
timestamp=lambda s:float(re.search(r'\[\s*(\d+\.\d+)\]',s)[1]);fields=re.search(r'response=(\d+) firmware=([0-9a-f]+) expired=(\d+)',response)
tail=[line for value in inventory['pstore_b64'].values() for line in base64.b64decode(value).decode(errors='replace').splitlines()
 if re.search(r'\[\s*(\d+\.\d+)\]',line) and timestamp(line)>=timestamp(release)]
files=list((P/'collected-r1').iterdir());assert not any(p.name.startswith('firmware-') or p.name.startswith('a5-devcd') for p in files)
report=dict(stage=371,run='r1',passed=False,normal_terminal=False,old_phase=state['phase'],old_worker_live=False,collector_live=False,new_boot_observed=True,
 hold_start_failure_explicit=True,worker_payload_matches_manifest=True,collector_armed_before_boot_module=state['collector_armed_before_boot_module'],
 init_response=int(fields[1]),firmware_version_register=int(fields[2],16),deadline_expired=bool(int(fields[3])),
 fatal_response_latency_ms=round((timestamp(response)-timestamp(release))*1000,3),
 block_reset_assertion_logged=any('A5 stopped, block reset asserted' in line for line in lines),
 dma_retirement_stage_logged=any('A5 retiring DMA aliases' in line for line in lines),dma_retired_stage_logged=any('A5 DMA aliases retired' in line for line in lines),
 pm_release_stage_logged=any('A5 PM reference released' in line for line in lines),
 held_window_return_observed=False,standard_devcoredump_recovered=False,firmware_ram_snapshot_recovered=False,
 exact_reset_cause_proven=False,modem_watchdog_in_collected_pstore=any(re.search(r'watchdog received|crash detected in modem',line) for line in tail),host_reset_sent=False,
 no_successful_dma_pm_cleanup_claim=True,firmware_handshake_passed=False)
for name in ['boot-runtime-r1-validation.json','boot-runtime-validation.json']:(HERE/name).write_text(json.dumps(report,indent=2)+'\n')
source=json.loads((HERE/'source-state.json').read_text());source.update(firmware_cpu_started=True,temporary_runtime_exercised=True,installed=False,hardware_boot_verified=False,hardware_cleanup_verified=False,runtime_evidence='reference/kernel371/boot-runtime-r1-validation.json',current_device_recovered=True)
(HERE/'source-state.json').write_text(json.dumps(source,indent=2)+'\n');print(json.dumps(report,indent=2))
