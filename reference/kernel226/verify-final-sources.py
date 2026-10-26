from pathlib import Path
import hashlib
import json
import re
import tarfile
from loc_decode import regression

here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel226')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p in here.glob('*.py'):compile(p.read_text(),str(p),'exec')
proofs=[('loc-session-r1.c','loc-session-build-validation.json','k226-loc-tools'),
        ('loc-session-r2.c','loc-session-r2-build-validation.json','k226-loc-tools-r2'),
        ('loc-session.c','loc-session-r3-build-validation.json','k226-loc-tools-r3')]
with tarfile.open(private/'final-evidence-aided-private.tar.gz') as tar:
 for source,proof_name,native in proofs:
  proof=json.loads((here/proof_name).read_text())
  assert sha(here/source)==proof['source_sha256']
  assert tar.extractfile(native+'/loc-session.c').read()==(here/source).read_bytes()
  binary=tar.extractfile(native+'/loc-session').read()
  assert hashlib.sha256(binary).hexdigest()==proof['binary_sha256']
  assert binary[:4]==b'\x7fELF' and int.from_bytes(binary[18:20],'little')==183
 for label in ['default','high','default-aided','high-aided']:
  report=json.loads((here/('loc-r3-'+label+'-validation.json')).read_text())
  assert report['decoder_sha256']==sha(here/'loc_decode.py')
  assert report['source_sha256']==sha(here/'loc-session.c')
  state=json.loads(tar.extractfile('k226-loc-r3-'+label+'/state-private.json').read())
  assert state['terminal'] and state['exit_code']==0 and state['cleanup']['stop_ack']
 assert len(tar.getmembers())==117
requests={int(x,16) for x in re.findall(r'request_new\(client, (0x[0-9a-f]+)\)',(here/'loc-session.c').read_text())}
assert requests=={0x21,0x22,0x23,0x32,0x33,0x3f,0x4b}
layout=json.loads((here/'loc-layout-source-validation.json').read_text())
for name,record in layout['sources'].items():assert sha(private/'qualcomm-loc-public-sources'/name)==record['sha256']
header=(private/'qualcomm-loc-public-sources/location_service_v02.h').read_text()
assert 'eQMI_LOC_SESS_STATUS_USER_END_V02 = 4' in header
assert 'eQMI_LOC_SESS_STATUS_TIMEOUT_V02 = 3' in header
final=json.loads((here/'final-validation.json').read_text());assert final['total_requested_observation_seconds']==360 and final['positive_cnr_tracking_and_real_fix_still_not_observed']
health=json.loads((here/'post-aiding-health-validation.json').read_text());assert health['taint']==0 and not any(health['fault_counts'].values()) and health['nv_sources_unchanged']
assert json.loads((here/'final-evidence-aided-validation.json').read_text())['verified_members']==117
assert json.loads((here/'final-evidence-validation.json').read_text())['verified_members']==87
recipe=repo/'linux-port/packages/libcamera';lock=json.loads((recipe/'source-lock.json').read_text())
assert lock['stage']==225 and lock['new_recipe_version']=='99990.7.2-r13'
assert all(sha(recipe/n)==v for n,v in lock['source_files_sha256'].items())
deployment=json.loads((repo/'linux-port/camera/deployment-lock.json').read_text())
assert deployment['stage']==225 and deployment['configuration_version']=='0.1.0-r8'
assert (repo/'NEXT-SESSION.md').stat().st_size<=6500
for title in ['## 源码、产物与回退依据','## 续作与已知风险']:assert title in (repo/'NEXT-SESSION.md').read_text()
assert (repo/'archive/NEXT-SESSION-through225-2026-10-16.md').stat().st_size==5606
report=dict(stage=226,python_sources_compile=len(list(here.glob('*.py'))),three_native_c_revisions_and_elf_hashes_verified=True,
 r1_r2_diagnostics_preserved_not_counted_as_formal_tests=True,raw_loc_message_allowlist_verified=sorted(requests),
 parser_regression=regression(),four_formal_contexts_terminal_and_cleanup_verified=True,
 official_observation_seconds=360,archive_members=117,pre_aiding_archive_members=87,
 fixed_public_layout_sources_verified=True,position_status4_decoded_as_user_end=True,
 canonical_r13_r8_sources_and_deployment_locks_preserved=True,
 next_session_bytes=(repo/'NEXT-SESSION.md').stat().st_size,full_peripheral_goal_active=True)
(here/'source-final-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
