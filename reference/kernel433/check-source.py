"""Verify actual candidate source, matching modules, replay and build restoration."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage433source',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);build=m.mounted_build();kernel=build.parent/'source354'
state=json.loads((HERE/'source-state.json').read_text());git=lambda *a:subprocess.check_output(['git','-C',str(kernel),*a])
assert git('rev-parse','HEAD').decode().strip()==state['commit'] and not git('status','--porcelain')
assert json.loads((HERE/'driver-validation.json').read_text())['source_commit']==state['commit']
replay=P/'patch-replay';replay.mkdir(exist_ok=True)
for row in state['source_hashes']:
 path=kernel/row['path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256'];out=replay/row['path'];out.parent.mkdir(parents=True,exist_ok=True)
 q=subprocess.run(['git','-C',str(kernel),'show',state['parent_commit']+':'+row['path']],capture_output=True)
 if q.returncode:
  assert path.name in ['camss-vfe-175-gtm.c','camss-vfe-175-gtm.h']
  if out.exists():assert out.resolve().is_relative_to(replay.resolve());out.unlink()
 else:out.write_bytes(q.stdout)
q=subprocess.run(['patch','--batch','--fuzz=0','-p1','-i',str(HERE/'gtm-driver.patch')],cwd=replay,capture_output=True);(P/'patch-replay-private.log').write_bytes(q.stdout+q.stderr);assert not q.returncode and b'fuzz' not in q.stdout and b'offset' not in q.stdout
for row in state['source_hashes']:assert (replay/row['path']).read_bytes()==(kernel/row['path']).read_bytes()
terminal=json.loads((P/'intree-build-state.json').read_text());assert terminal['terminal'] and terminal['passed'] and terminal['attempt']==2
report=json.loads((HERE/'intree-build-validation.json').read_text());assert report['passed'] and not report['diagnostics'] and len(report['modules'])==10
for row in report['modules']:assert hashlib.sha256(Path(row['private_path']).read_bytes()).hexdigest()==row['sha256']
camss=next(r for r in report['modules'] if r['name']=='qcom-camss');symbols=subprocess.check_output(['aarch64-linux-gnu-nm',camss['private_path']],text=True)
for name in ['vfe_175_gtm_encode','vfe_175_gtm_params','vfe_175_gtm_ack','vfe_175_gtm_tag','vfe_175_gtm_fill','vfe_params_apply_next']:assert any(l.endswith(' T '+name) for l in symbols.splitlines()),name
old=json.loads((HERE.parent/'kernel431/intree-build-validation.json').read_text())
for name in ['qcom-camss-icp-a5-core','camss-icp-a5-m2m']:assert next(r for r in report['modules'] if r['name']==name)['sha256']==next(r for r in old['modules'] if r['name']==name)['sha256']
backup=P/'intree-build-r2-before'
for directory in ['drivers/media/platform/qcom/camss','drivers/media/v4l2-core','drivers/media/common/videobuf2']:
 before=backup/directory;after=build/directory
 assert {str(p.relative_to(before)) for p in before.rglob('*') if p.is_file()}=={str(p.relative_to(after)) for p in after.rglob('*') if p.is_file()}
 for p in before.rglob('*'):
  if p.is_file():assert p.read_bytes()==(after/p.relative_to(before)).read_bytes()
r=dict(stage=433,commit=state['commit'],source_clean=True,source_hashes_match=True,patch_replays_without_fuzz_or_offset=True,actual_camss_module_has_gtm_and_ack_symbols=True,matching_module_hashes_verified=True,modules_built=10,w1_werror_diagnostics=0,icp_core_and_m2m_unchanged_from431=True,shared_build_module_directories_restored=True,typed_payload_and_stats_sizes_verified_by_host_arm64=True,board_dt_and_sensor_sources_unchanged=True,production_ipa_still431_candidate=True,phone_accessed=False,installed=False,passed=True)
(HERE/'source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
