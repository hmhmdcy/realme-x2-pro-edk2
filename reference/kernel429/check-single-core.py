"""Audit the fixed single-core replay without conflating completion and DC proof."""
from pathlib import Path
import hashlib,json,struct,zlib
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;root=P/'runtime-collected-r4'
s=json.loads((root/'state.json').read_text())
assert s['terminal'] and s['passed'] and s['formal_modules_restored'] and s['services_restored']
assert not s['new_faults'] and s['taint_before']==s['taint_after']==0
c=s['candidate_final_status'];assert c['jobs']==c['completed']==c['direct_completed']==4
build=json.loads((HERE/'intree-build-r3-validation.json').read_text())
proof=json.loads((P/'runtime-proof-private.json').read_text())
assert s['candidate_notes']=={n:r['note_sha256'] for n,r in proof['modules'].items()}
assert {r['sha256'] for r in build['modules'] if r['runtime_candidate']}=={r['sha256'] for r in proof['modules'].values()}
lines=(root/'replay/client.log').read_text().splitlines();frames=[json.loads(l) for l in lines if l.startswith('{')]
assert len(frames)==4 and len({f['full_hash'] for f in frames})==1 and frames[0]['pd10_hash']==frames[3]['pd10_hash']
rows=[];outputs=[]
for mode,f in enumerate(frames):
 assert f['mode']==mode and f['passed']
 raw=(root/f'replay/mode-{mode}-scratch-private.bin').read_bytes();request,size,crc,changed=struct.unpack_from('<4I',raw)
 assert request==1 and size==71488 and len(raw)==size+16 and crc==zlib.crc32(raw[16:])
 assert changed==sum(x!=0xa7 for x in raw[16:])==f['scratch_changed_bytes']
 out=(root/f'replay/mode-{mode}-output-private.bin').read_bytes();assert len(out)==460800;outputs.append(out)
 rows.append(dict(mode=mode,scratch_bytes=size,scratch_changed_from_prefill_bytes=changed,output_sha256=hashlib.sha256(out).hexdigest(),driver_completion=True))
differences=sum(a!=b for a,b in zip(outputs[0],outputs[3]))
report=dict(stage=429,attempt='r4',scope='Fixed single-core transport and evidence audit; not DC or quality acceptance',
 actual_build_attempt=3,actual_source_commit=json.loads((HERE/'source-state.json').read_text())['commit'],
 complete_direct_jobs=4,cores=1,rows=rows,repeat_real_output_different_bytes=differences,
 repeat_real_luma_mean_absolute_difference=sum(abs(a-b) for a,b in zip(outputs[0][:307200],outputs[3][:307200]))/307200,
 repeatability_verified=differences==0,dc_statistics_writeout_verified=False,ltm_dc_consumption_verified=False,
 single_core_did_not_resolve_repeatability=differences>0,live_sensor_capture=False,source_full_pd10_same_sof_from428=True,
 automatic_ipa_mathematical_history_commits=0,gtm_applied_version_correlated=False,feature_acceptance_passed=False,
 formal_modules_services_and_resources_restored=True,new_related_faults=0,taint_after=0,evidence_and_transport_audit_passed=True,passed=True)
(HERE/'single-core-hardware-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
