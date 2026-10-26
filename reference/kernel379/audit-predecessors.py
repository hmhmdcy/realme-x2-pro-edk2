from pathlib import Path
import json,re
HERE=Path(__file__).resolve().parent;BASE=Path('/mnt/e/edk2-samurai-out')
for stage in [377,378]:
 p=BASE/('kernel'+str(stage));text=(p/'a5-ramoops-excerpt-private.txt').read_text();marker='A5 diagnostic run begin after binding';start=text.rindex(marker);window=text[start:]
 assert 'A5 IPE create acknowledged type=2 active=1' in window and 'diagnostic run end ret=-121 init=1 ping=1 pc=0' in window
 assert all(m in window for m in ['A5 stopped, cooperative=0 block_reset=1','A5 DMA aliases retired','A5 PM reference released: 0'])
 assert 'IPE create acknowledged type=3' not in window and 'SYS_PC_PREP acknowledged' not in window
 if stage==377:assert 'config region map acknowledged' not in window and 'CONFIG_IO acknowledged' not in window
 else:assert 'config region map acknowledged' in window and 'CONFIG_IO acknowledged scratch=48' in window and 'opcode=15 failed ret=-121 hfi=0 status=1773264' in window
 inventory=json.loads((p/'recovered-inventory-private.json').read_text());assert not inventory['r5_state']['terminal']
 report=dict(stage=stage,latest_run_window_only=True,initial_rt_create_acknowledged=True,non_rt_create_not_reached=True,
  config_map_acknowledged=stage==378,config_io_acknowledged=stage==378,unmap_ack_misparsed=stage==378,
  failure_at_first_map=stage==377,returned_error=-121,normal_pc_ack_not_reached=True,forced_reset_and_dma_pm_release_logged=True,
  automatic_new_boot_observed=True,host_reset_sent=False,old_worker_terminal_not_persisted=True,normal_terminal_cleanup_not_proven=True,
  actual_377_firmware_error_code_not_recorded=stage==377,actual_378_unmap_header_succeeded_but_unspecified_tail_misread=stage==378,
  full_image_pipeline_verified=False,raw_evidence_private=True)
 (HERE.parent/('kernel'+str(stage))/'attempt-audit-validation.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report))
