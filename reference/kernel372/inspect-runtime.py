from pathlib import Path
import base64,hashlib,json,re
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
d=json.loads((P/'recovered-inventory-private.json').read_text());observed=json.loads((P/'observation-r1-private.json').read_text());snapshot=json.loads((HERE/'pre-reset-runtime-validation.json').read_text())
assert not observed['same_boot'] and not observed['worker_live'] and not observed['collector_live'] and not observed['state']['terminal']
lines=(P/'a5-ramoops-excerpt-private.txt').read_text().splitlines();release=next(line for line in lines if 'A5 CPU release' in line);response=next(line for line in lines if 'A5 HFI response=' in line)
stamp=lambda s:float(re.search(r'\[\s*(\d+\.\d+)\]',s)[1]);fields=re.search(r'response=(\d+) firmware=([0-9a-f]+) expired=(\d+)',response)
report=dict(stage=372,run='r1',passed=False,normal_terminal=False,new_boot_observed=True,old_worker_live=False,collector_live=False,
 init_response=int(fields[1]),firmware_version_register=int(fields[2],16),deadline_expired=bool(int(fields[3])),fatal_response_latency_ms=round((stamp(response)-stamp(release))*1000,3),
 pre_reset_code_page_match=snapshot['code_page_match_observed'],pre_reset_snapshot_complete=snapshot['complete_exception_snapshot'],pre_reset_words=snapshot['words'],
 real_exception_function=snapshot.get('fault_pc_function'),standard_devcoredump_recovered=False,sfr_buffer_text_recovered=False,
 original_handler_exception_text_recovered_in_abort_stack=True,block_reset_assertion_logged=any('A5 stopped, block reset asserted' in line for line in lines),
 dma_retirement_stage_logged=any('A5 retiring DMA aliases' in line for line in lines),pm_release_stage_logged=any('A5 PM reference released' in line for line in lines),
 exact_reset_cause_proven=False,host_reset_sent=False,firmware_handshake_passed=False)
for name in ['boot-runtime-r1-validation.json','boot-runtime-validation.json']:(HERE/name).write_text(json.dumps(report,indent=2)+'\n')
p=HERE/'source-state.json';s=json.loads(p.read_text());s.update(firmware_cpu_started=True,temporary_runtime_exercised=True,pre_reset_observer_hardware_verified=True,hardware_boot_verified=False,hardware_cleanup_verified=False,installed=False);p.write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps(report,indent=2))
