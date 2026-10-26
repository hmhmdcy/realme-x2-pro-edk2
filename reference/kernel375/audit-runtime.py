from pathlib import Path
import json,re
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
d=json.loads((HERE/'boot-runtime-validation.json').read_text());assert d['passed'] and d['same_boot'] and d['terminal'] and not d['worker_live'] and not d['collector_live']
text=(P/'collected-r1/kernel-log-private.txt').read_text()
markers=['diagnostic overlay apply end ret=0 bound=1','diagnostic run begin after binding','HFI parameters verified after CPU reset','HFI response=1','SYS_INIT acknowledged','SYS_PING acknowledged','SYS_PC_PREP acknowledged','A5 stopped, cooperative=1 block_reset=0 pc_error=0','A5 retiring DMA aliases','A5 DMA aliases retired','A5 PM reference released: 0','diagnostic run end ret=0 init=1 ping=1 pc=1','diagnostic module exit begin','diagnostic overlay remove ret=0','diagnostic module exit end']
indices=[text.index(marker) for marker in markers];assert indices==sorted(indices)
m=re.search(r'\[\s*([\d.]+)\].*A5 CPU release',text);n=re.search(r'\[\s*([\d.]+)\].*A5 HFI response=1',text)
report=dict(stage=375,all_markers_in_order=True,actual_init_ping_pc_acknowledged=True,actual_cooperative_stop_without_block_reset=True,
 dma_retired_before_pm_release=True,explicit_run_returned=True,overlay_removed=True,module_exit_returned=True,same_boot=True,
 ready_response_latency_ms=round((float(n[1])-float(m[1]))*1000,3),full_hfi_lifecycle_verified=True,
 image_sessions=0,ipe_image_processing_verified=False,exact_hardware_failure_mechanism_of_prior_reboot_proven=False,
 raw_evidence_private=True,passed=True)
(HERE/'lifecycle-runtime-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
