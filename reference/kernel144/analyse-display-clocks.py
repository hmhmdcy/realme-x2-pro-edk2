from pathlib import Path
import hashlib
import json
import re
import tarfile
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel144');out=Path('/mnt/e/edk2-samurai-out/kernel144')
archives=[('legacy140-startup',out.parent/'kernel142/reboot140-startup-private.tar.gz'),
    ('threaded143-startup',out.parent/'kernel143/first143-startup-private.tar.gz'),
    ('current140-idle',out/'current140-private.tar.gz')]
reports=[]
for label,path in archives:
    selected={}
    with tarfile.open(path,mode='r|gz') as archive:
        for member in archive:
            name=member.name.removeprefix('./')
            if member.isfile() and (name=='SHA256SUMS' or name in ['clocks-final-private.txt','clocks-private.txt','drm-final-private.txt','drm-state-private.txt','dmesg-final-private.txt','dmesg-private.txt','startup-result.json','baseline-validation.json']):
                selected[name]=archive.extractfile(member).read()
    manifest={name.removeprefix('./'):digest for digest,name in (line.split('  ',1) for line in selected['SHA256SUMS'].decode().splitlines())}
    assert all(hashlib.sha256(data).hexdigest()==manifest[name] for name,data in selected.items() if name!='SHA256SUMS')
    clocks=selected.get('clocks-final-private.txt',selected.get('clocks-private.txt')).decode()
    state=selected.get('drm-final-private.txt',selected.get('drm-state-private.txt')).decode()
    dmesg=selected.get('dmesg-final-private.txt',selected.get('dmesg-private.txt')).decode()
    rows={}
    for line in clocks.splitlines():
        parts=line.split()
        if parts and re.search(r'disp_cc_mdss|dsi0|gcc_disp|mdp_clk',parts[0]):rows[parts[0]]=parts[1:]
    dsi=[line for line in dmesg.splitlines() if 'dsi_err_worker: status=' in line]
    stamps=[float(re.search(r'\[\s*(\d+\.\d+)\]',line)[1]) for line in dsi]
    report=dict(label=label,selected_manifest_hashes_verified=True,display_active='active=1' in state,
        dsi_status_log_lines=len(dsi),first_dsi_status_uptime=stamps[0] if stamps else None,
        last_dsi_status_uptime=stamps[-1] if stamps else None,
        dsi_status_values=sorted(set(line.split('status=',1)[1] for line in dsi)),
        dpu_timeouts=dmesg.count('frame done timeout'),display_clock_rows=rows)
    reports.append(report)
out.joinpath('display-clock-comparison-private.json').write_text(json.dumps(reports,indent=2)+'\n')
summary=dict(stage=144,previous_goal_turn_classification='progress',snapshots=reports,
    different_boot_snapshots_not_a_controlled_clock_experiment=True,
    idle_snapshot_cannot_prove_active_bandwidth_contract=True,display_accepted=False,goal_complete=False)
ref.joinpath('display-clock-comparison-validation.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
