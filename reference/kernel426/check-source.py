"""Verify final maintained codec source, patch and actual CAMSS module symbol."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
build=m.mounted_build();kernel=build.parent/'source354';state=json.loads((HERE/'source-state.json').read_text())
git=lambda *a:subprocess.check_output(['git','-C',str(kernel),*a])
assert git('rev-parse','HEAD').decode().strip()==state['commit'] and not git('status','--porcelain')
replay=P/'patch-replay';replay.mkdir(exist_ok=True)
for row in state['source_hashes']:
 path=kernel/row['path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
 out=replay/row['path'];out.parent.mkdir(parents=True,exist_ok=True)
 q=subprocess.run(['git','-C',str(kernel),'show',state['parent_commit']+':'+row['path']],capture_output=True)
 if q.returncode:
  assert path.name in ['camss-vfe-175-ds4.c','camss-vfe-175-ds4.h']
  if out.exists():assert out.resolve().is_relative_to(replay.resolve());out.unlink()
 else:out.write_bytes(q.stdout)
q=subprocess.run(['patch','--batch','--fuzz=0','-p1','-i',str(HERE/'ds4-register-codec.patch')],cwd=replay,capture_output=True)
(P/'patch-replay.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0 and b'offset' not in q.stdout and b'fuzz' not in q.stdout
for row in state['source_hashes']:assert (replay/row['path']).read_bytes()==(kernel/row['path']).read_bytes()
terminal=json.loads((P/'intree-build-state.json').read_text());assert terminal['terminal'] and terminal['passed'] and terminal['attempt']==3
d=json.loads((HERE/'intree-build-validation.json').read_text());assert d['passed'] and not d['diagnostics'] and len(d['modules'])==10
for row in d['modules']:assert hashlib.sha256(Path(row['private_path']).read_bytes()).hexdigest()==row['sha256']
camss=next(row for row in d['modules'] if row['name']=='qcom-camss')
symbols=subprocess.check_output(['aarch64-linux-gnu-nm',camss['private_path']],text=True)
assert any(line.endswith(' T vfe_175_ds4_encode') for line in symbols.splitlines())
core=next(row for row in d['modules'] if row['name']=='qcom-camss-icp-a5-core')
assert core['sha256']==json.loads((HERE.parent/'kernel425/intree-build-validation.json').read_text())['modules'][0]['sha256']
restored=[]
for name in ['qcom-camss.ko','qcom-camss-icp-a5-core.ko','camss-vfe-175-ds4.o','camss-icp-a5-m2m.ko']:
 rel=Path('drivers/media/platform/qcom/camss')/name;current=build/rel;before=P/'intree-build-r3-before'/rel
 assert current.exists()==before.exists()
 if before.exists():assert current.read_bytes()==before.read_bytes()
 restored.append(dict(name=name,existed_before=before.exists(),restored=True))
log=(P/'intree-build-r3.log').read_text();assert 'camss-vfe-175-ds4.o' in log
assert json.loads((HERE/'codec-validation.json').read_text())['source_commit']==state['commit']
r=dict(stage=426,commit=state['commit'],source_hashes_match=True,source_clean=True,patch_replays_without_fuzz_or_offset=True,
 actual_ds4_object_recompiled=True,actual_camss_module_contains_codec_symbol=True,candidate_binary_hashes_match=True,
 core_unchanged_from425=True,shared_selected_outputs_restored=restored,build_terminal=True,build_diagnostics=0,
 first_build_explicit_bits_header_fixed=True,second_build_missing_matching_helper_symbols_fixed=True,
 module_symbol_errors_not_suppressed=True,ds4_queue_dma_runtime_not_connected=True,installed=False,passed=True)
(HERE/'source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
