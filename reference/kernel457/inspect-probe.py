"""Report the cached read-only runtime capability probe; no live device access."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
private=Path('/mnt/e/edk2-samurai-out/kernel457')
probe=private/'trace-capabilities-private.json';extra=private/'trace-extra-private.json'
p=json.loads(probe.read_text());e=json.loads(extra.read_text())
assert p['phone_changed'] is False and e['phone_changed'] is False
assert p['instances_supported'] and p['charging_before']==p['charging_after']
assert all(p['wanted_events'].values()) and set(p['formats'])==set(p['wanted_events'])
assert p['tracefs']=='/sys/kernel/tracing' and 'mono' in p['trace_clock'].split()
assert p['existing_instances']==['display','radio'] and p['tracing_on']=='1'
assert p['online_cpus']==e['online_cpus']=='0-7'
assert p['video_nodes']['video0']==dict(name='msm_vfe0_video0',dev='81:0')
assert p['video_nodes']['video3']==dict(name='msm_vfe0_video3',dev='81:3')
report=dict(stage=457,read_only_live_probe_passed=True,events_available=p['wanted_events'],
 instances_supported=True,mono_available=True,existing_display_radio_retained_at_probe=True,
 online_cpu_count=8,all_available_events_proven_emitted=False,
 video0_role_not_proven_by_probe=True,full_role_requires_media_topology_and_fd_evidence=True,
 probe_sha256=hashlib.sha256(probe.read_bytes()).hexdigest(),extra_sha256=hashlib.sha256(extra.read_bytes()).hexdigest(),
 phone_accessed_by_this_checker=False,phone_changed_by_probe=False,passed=True)
(HERE/'probe-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
