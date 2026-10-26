from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage434source',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);K=m.mounted_build().parent/'source354'
state=json.loads((HERE/'source-state.json').read_text());git=lambda *a:subprocess.check_output(['git','-C',str(K),*a])
assert git('rev-parse','HEAD').decode().strip()==state['commit'] and not git('status','--porcelain')
assert git('diff',state['parent_commit'],state['commit'],'--name-only').decode().splitlines()==state['files']
assert git('diff',state['parent_commit'],state['commit'],'--').decode()==(HERE/'gtm-reopen.patch').read_text()
replay=P/'patch-replay';replay.mkdir(exist_ok=True)
for rel in state['files']:
 out=replay/rel;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(git('show',state['parent_commit']+':'+rel))
q=subprocess.run(['patch','--batch','--fuzz=0','-p1','-i',str(HERE/'gtm-reopen.patch')],cwd=replay,capture_output=True);assert not q.returncode and b'fuzz' not in q.stdout and b'offset' not in q.stdout
for rel in state['files']:assert (replay/rel).read_bytes()==(K/rel).read_bytes()
report=json.loads((HERE/'intree-build-validation.json').read_text());assert report['passed'] and not report['diagnostics'] and len(report['modules'])==10
assert json.loads((P/'intree-build-state.json').read_text())['terminal']
for row in report['modules']:assert hashlib.sha256(Path(row['private_path']).read_bytes()).hexdigest()==row['sha256']
prior=json.loads((HERE.parent/'kernel433/intree-build-validation.json').read_text())
for name in ['qcom-camss-icp-a5-core','camss-icp-a5-m2m']:assert next(r for r in report['modules'] if r['name']==name)['sha256']==next(r for r in prior['modules'] if r['name']==name)['sha256']
r=dict(stage=434,commit=state['commit'],kernel_clean=True,only_17x_initial_pix_parameter_order_changed=True,patch_replays_without_fuzz_or_offset=True,matching_ten_modules_built=True,w1_werror_diagnostics=0,icp_core_and_m2m_unchanged_from431=True,live_gtm_ack_sof_driver_bodies_unchanged_from433=True,board_dt_sensors_and_production_ipa_unchanged=True,passed=True)
(HERE/'source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
