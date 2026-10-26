from pathlib import Path
import base64,json,re
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
d=json.loads((P/'recovered-inventory-private.json').read_text());observed=json.loads((P/'observation-r1-private.json').read_text())
assert not observed['same_boot'] and not observed['worker_live'] and not observed['collector_live'] and not observed['state']['terminal']
lines=(P/'a5-ramoops-excerpt-private.txt').read_text().splitlines();release=next(line for line in lines if 'A5 CPU release' in line);response=next(line for line in lines if 'A5 HFI response=' in line)
stamp=lambda s:float(re.search(r'\[\s*(\d+\.\d+)\]',s)[1]);fields=re.search(r'response=(\d+) firmware=([0-9a-f]+) expired=(\d+)',response)
ready=int(fields[1])==1;sysinit=any('A5 SYS_INIT acknowledged' in line for line in lines)
assert ready and sysinit and any('A5 HFI parameters verified after CPU reset' in line for line in lines)
report=dict(stage=373,run='r1',passed=False,normal_terminal=False,new_boot_observed=True,old_worker_live=False,collector_live=False,
 init_response=int(fields[1]),firmware_version_register=int(fields[2],16),deadline_expired=bool(int(fields[3])),ready_response_latency_ms=round((stamp(response)-stamp(release))*1000,3),
 ten_bootstrap_register_readbacks_verified=True,actual_sys_init_acknowledged=sysinit,
 pc_prepare_and_wfi_returned_zero_observed=any('pc_error=0' in line for line in lines),pc_result_inferred_from_executed_production_path=True,
 ping_ack_durably_verified=False,dma_retirement_completed_logged=any('A5 DMA aliases retired' in line for line in lines),
 pm_release_return_zero_logged=any('A5 PM reference released: 0' in line for line in lines),
 successful_start_did_not_invoke_failure_snapshot=not any('A5 pre-reset snapshot begin' in line for line in lines),
 exact_reboot_cause_proven=False,host_reset_sent=False,full_firmware_handshake_passed=False,hardware_cleanup_verified=False)
for name in ['boot-runtime-r1-validation.json','boot-runtime-validation.json']:(HERE/name).write_text(json.dumps(report,indent=2)+'\n')
p=HERE/'source-state.json';s=json.loads(p.read_text());s.update(firmware_cpu_started=True,temporary_runtime_exercised=True,hardware_sys_init_verified=True,hardware_full_handshake_verified=False,hardware_cleanup_verified=False,installed=False);p.write_text(json.dumps(s,indent=2)+'\n')
pre=HERE/'pre-reset-runtime-validation.json';s=json.loads(pre.read_text());s.update(not_applicable_after_start_success=True,decode_status='Failure observer not invoked on successful SYS_INIT start');pre.write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps(report,indent=2))
