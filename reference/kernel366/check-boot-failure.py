"""Publish bounded A5 evidence from private ramoops, retaining missing terminal."""
from pathlib import Path
import json,re
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=(P/'recovered-console-ramoops-0-private').read_text(errors='replace')
need=['Firmware memory resolves to /reserved-memory/memory@9ab00000, no-map=1',
 'A5 firmware and shared aliases ready; firmware privileged','A5/BPS/IPE resources powered',
 'A5 CPU release, HFI request prepared','A5 HFI response=3 firmware=1000100 expired=1',
 'A5 stopped, block reset asserted; pc_error=0','remoteproc remoteproc1: crash detected in modem: type watchdog']
positions=[s.index(n) for n in need];assert positions==sorted(positions)
lines=[line for line in s.splitlines() if any(n in line for n in need)]
old=json.loads((P/'recovered-inventory-private.json').read_text())['r5_state'];assert old['phase']=='load-boot-test' and old['terminal'] is False
report=dict(stage=366,run='r1',passed=False,original_transaction_terminal=False,
    original_transaction_preserved=True,old_worker_absent_after_new_boot=True,
    board_firmware_reference_resolved=True,firmware_alias_setup_completed=True,icp_resources_powered=True,
    a5_cpu_release_attempted=True,hfi_init_response=3,firmware_version_register=0x01000100,
    exact_ready_timed_out=True,block_reset_asserted_logged=True,
    complete_sys_init_ping_pc_ack_verified=False,cleanup_completion_not_observed=True,
    modem_watchdog_followed=True,new_linux_boot_observed=True,explicit_host_reset_sent=False,
    modem_watchdog_root_cause_unproven=True,new_automatic_cpu_release_experiments_prepared=False,
    next_step='Inspect original firmware response-3 writes, HFI scratch/CSR semantics and power-down ordering offline before another CPU release.',
    bounded_kernel_evidence=lines)
(HERE/'boot-runtime-r1-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(HERE/'boot-runtime-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
