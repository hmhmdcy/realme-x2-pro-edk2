from pathlib import Path
import json,re
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
text=(P/'a5-ramoops-excerpt-private.txt').read_text();observation=json.loads((P/'observation-r1-private.json').read_text());state=observation['state']
markers=['diagnostic probe ready; no firmware started','diagnostic bus event=bound','diagnostic overlay apply end ret=0 bound=1','diagnostic run begin after binding','HFI parameters verified after CPU reset','HFI response=1','SYS_INIT acknowledged','SYS_PING acknowledged','SYS_PC_PREP acknowledged','A5 stopped, block reset asserted; pc_error=0']
indices=[text.index(marker) for marker in markers];assert indices==sorted(indices)
assert state['binding_returned_before_cpu_release'] and state['phase']=='explicit-post-bind-run' and not state['terminal']
m=re.search(r'\[\s*([\d.]+)\].*A5 CPU release',text);n=re.search(r'\[\s*([\d.]+)\].*A5 HFI response=1',text)
report=dict(stage=374,normal_platform_binding_returned_before_cpu_release=True,overlay_apply_returned=True,
 actual_sys_init_acknowledged=True,actual_sys_ping_acknowledged=True,actual_sys_pc_prepare_acknowledged=True,
 pc_prepare_and_wfi_zero_error_logged=True,ready_response_latency_ms=round((float(n[1])-float(m[1]))*1000,3),
 normal_terminal=False,full_firmware_handshake_passed=False,hardware_cleanup_verified=False,
 actual_dma_retirement_started='A5 retiring DMA aliases' in text,actual_dma_retirement_completed='A5 DMA aliases retired' in text,
 pm_reference_release_observed='A5 PM reference released' in text,system_reboot_after_explicit_post_bind_run=not observation['same_boot'],
 precise_reset_cause_known=False,host_reset_sent=False,raw_evidence_private=True)
(HERE/'boot-runtime-r1-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
