"""Keep crash/authentication logs private; publish only a small boot summary."""
from pathlib import Path
import base64,json,re
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
q=host.raw_ssh('python3 -',input=(HERE/'recovery-inventory-device.py').read_bytes(),timeout=40)
facts=json.loads(q.stdout);(P/'recovered-inventory-secret-private.json').write_bytes(q.stdout)
rawdir=P/'recovered-pstore-secret-private';rawdir.mkdir(mode=0o700,exist_ok=True)
for name,data in facts['pstore_b64'].items():assert Path(name).name==name;(rawdir/name).write_bytes(base64.b64decode(data))
(P/'recovered-current-dmesg-secret-private.log').write_bytes(base64.b64decode(facts['current_dmesg_b64']))
patterns=dict(panic=r'Kernel panic',rcu_stall=r'rcu.*stall|RCU.*stall',nmi=r'NMI',watchdog=r'watchdog',
    smmu_fault=r'arm-smmu.*[Ff]ault|IOMMU.*[Ff]ault|[Tt]ranslation fault',oops=r'Internal error|Oops:|SError',authentication_debug=r'eud.*(?:rx|RX)|sshd-auth')
pstore=[dict(file=name,bytes=len(base64.b64decode(data)),keyword_counts={k:len(re.findall(pattern,base64.b64decode(data).decode(errors='replace'))) for k,pattern in patterns.items()}) for name,data in facts['pstore_b64'].items()]
summary=dict(stage=360,strict_original_key_usb_ssh_restored=True,model_verified=True,kernel=facts['kernel'],new_boot_compared_with_previous_guards=not any(facts['old_guard_matches'].values()),
    uptime_seconds=facts['uptime_seconds'],taint=int(facts['taint']),cpu_online=facts['cpu_online'],
    camss_matches_released338=facts['camss_build_note_sha256']=='0227d29bb5129e2fc69866529147b21b902d441c855f848fd5eaa3093c590297',
    icp_core_loaded=facts['modules']['qcom_camss_icp_a5_core'],icp_test_loaded=facts['modules']['camss_icp_a5_boot_test'],
    r5_state_present=facts['r5_state'] is not None,r5_previous_state_terminal=facts['r5_state'].get('terminal') if facts['r5_state'] else None,
    r5_previous_phase=facts['r5_state'].get('phase') if facts['r5_state'] else None,r5_worker_count=len(facts['worker_pids']),
    temporary_dt_nodes=len(facts['temporary_dt_nodes']),temporary_firmware_present=facts['temporary_firmware_present'],
    camss_runtime_status=facts['camss_runtime_status'],icp_bps_ipe_clocks=len(facts['icp_bps_ipe_clock_refs']),icp_bps_ipe_clock_refs_zero=not any(facts['icp_bps_ipe_clock_refs'].values()),
    pstore=pstore,raw_authentication_and_crash_logs_private=True,phone_mutations=0,package_candidate_installed=False)
(HERE/'recovered-boot-validation.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
