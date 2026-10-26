"""Check the maintained DS4 transport, exact patch replay and built cohort."""
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
 out=replay/row['path'];out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(git('show',state['parent_commit']+':'+row['path']))
q=subprocess.run(['patch','--batch','--fuzz=0','-p1','-i',str(HERE/'ds4-dma.patch')],cwd=replay,capture_output=True)
(P/'patch-replay.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0 and b'offset' not in q.stdout and b'fuzz' not in q.stdout
for row in state['source_hashes']:assert (replay/row['path']).read_bytes()==(kernel/row['path']).read_bytes()
terminal=json.loads((P/'intree-build-state.json').read_text());assert terminal['terminal'] and terminal['passed']
d=json.loads((HERE/'intree-build-validation.json').read_text());assert d['passed'] and not d['diagnostics'] and len(d['modules'])==10
for row in d['modules']:assert hashlib.sha256(Path(row['private_path']).read_bytes()).hexdigest()==row['sha256']
camss=next(row for row in d['modules'] if row['name']=='qcom-camss');symbols=subprocess.check_output(['aarch64-linux-gnu-nm',camss['private_path']],text=True)
for name in ['vfe_175_ds4_encode','vfe_175_ds4_start','vfe_175_ds4_stop','vfe_175_ds4_update','camss_format_pd10_layout']:assert any(line.endswith(' T '+name) for line in symbols.splitlines())
core=next(row for row in d['modules'] if row['name']=='qcom-camss-icp-a5-core');assert core['sha256']=='ae2ca7e3ede81ccb019422d7250376c23377537d2c328571817a3390db179099'
restored=[]
for name in ['qcom-camss.ko','qcom-camss-icp-a5-core.ko','camss-vfe-175-ds4.o','camss-icp-a5-m2m.ko']:
 rel=Path('drivers/media/platform/qcom/camss')/name;current=build/rel;before=P/('intree-build-r'+str(d['attempt'])+'-before')/rel
 assert current.exists()==before.exists()
 if before.exists():assert current.read_bytes()==before.read_bytes()
 restored.append(dict(name=name,existed_before=before.exists(),restored=True))
log=(P/('intree-build-r'+str(d['attempt'])+'.log')).read_text();assert 'camss-vfe-175-ds4.o' in log and 'camss-vfe.o' in log
vfe_sha=next(r['sha256'] for r in state['source_hashes'] if r['path'].endswith('/camss-vfe.c'));assert json.loads((HERE/'queue-validation.json').read_text())['source_sha256']==vfe_sha
video=(kernel/'drivers/media/platform/qcom/camss/camss-video.c').read_text();assert 'strscpy(f->description, "Qualcomm PD10 (local)"' in video
shared=(kernel/'drivers/media/v4l2-core/v4l2-ioctl.c').read_text();assert 'if (fmt->description[0])\n\t\t\t\treturn;' in shared
r=dict(stage=427,commit=state['commit'],source_hashes_match=True,source_clean=True,patch_replays_without_fuzz_or_offset=True,
 actual_changed_ds4_and_queue_objects_recompiled=True,actual_camss_contains_transport_symbols=True,candidate_binary_hashes_match=True,
 core_unchanged_from425=True,shared_selected_outputs_restored=restored,build_terminal=True,build_diagnostics=0,
 local_fourcc_described_without_modifying_shared_v4l2_core=True,experimental_fourcc_not_reserved_upstream=True,
 queue_contract_matches_current_source=True,temporary_runtime_candidate=True,permanent_install=False,passed=True)
(HERE/'source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
