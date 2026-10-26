"""Check the changed evidence and save a scoped local ADRC checkpoint."""
from pathlib import Path
import ast,hashlib,importlib.util,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=Path('/mnt/e/edk2-samurai-out/kernel409')
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);out=importlib.util.module_from_spec(spec);spec.loader.exec_module(out);return out
reports={name:json.loads((HERE/(name+'-validation.json')).read_text()) for name in ['adrc','packing','kernel-luts']}
assert all(r['passed'] for r in reports.values())
assert not json.loads((HERE/'packing-r1-validation.json').read_text())['passed']
assert reports['adrc']['valid_cases']==2783 and reports['adrc']['hal_vs_source_different_bytes']==0
assert reports['packing']['valid_cases']==reports['kernel-luts']['native_typed_cases']==2935
assert reports['kernel-luts']['compared_lut_bytes']==1502720 and reports['kernel-luts']['different_bytes']==0
assert all(r['passed'] and r['different_bytes']==0 for r in reports['packing']['rows'])
assert all(r['passed'] and r['records']==3978 for r in reports['kernel-luts']['temporal408_regression'])
for item in reports['packing']['current_source_hashes']:
    assert hashlib.sha256((HERE.parent/item['path']).read_bytes()).hexdigest()==item['sha256'],item['path']
storage=module('storage284',HERE.parent/'kernel284/storage.py');source=storage.mounted_build().parent/'source354'
state=json.loads((HERE/'source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
assert not state['phone_accessed'] and not state['installed'] and state['last_device_evidence_stage']==406
assert state['adrc_sampled_gain_conversion_verified'] and not state['full_ltm_numeric_math_complete']
index=module('session_index',ROOT/'linux-port/scripts/generate-session-index.py');(ROOT/'sessions/INDEX.md').write_text(index.render(ROOT))
check=module('docs_check',ROOT/'linux-port/scripts/docs-health-check.py');export=check.public_module(ROOT)
selected=[p.relative_to(ROOT) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected += [Path(p) for p in ['reference/kernel407/libipa/ltm_curves.cpp','reference/kernel407/README.md','NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md','sessions/INDEX.md','archive/NEXT-SESSION-through408-2026-10-21.md','linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json','linux-port/camera/README.md','linux-port/camera/kernel/README.md','linux-port/docs/HARDWARE-STATUS.md']]
for relative in selected:
    if relative.suffix=='.md':assert not check.link_errors(ROOT,str(relative)),(relative,check.link_errors(ROOT,str(relative)))
    if relative.suffix=='.py':ast.parse((ROOT/relative).read_text())
    if relative.suffix=='.json':json.loads((ROOT/relative).read_text())
limits=check.load_manifest(ROOT)['size_limits']
for p in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','DOCS-INDEX.md']:assert (ROOT/p).stat().st_size<=limits[p],(p,(ROOT/p).stat().st_size,limits[p])
for rel in ['linux-port/camera/deployment-lock.json','linux-port/camera/kernel/source-lock.json']:
    d=json.loads((ROOT/rel).read_text());assert d['latest_work_stage']==409 and d['current_device_revalidated_stage']==d['ipe_latest_hardware_stage']==406
    assert not d['latest_stage_phone_accessed'] and not d['latest_stage_device_mutated']
    assert d['ipe_ltm_adrc_sampled_gain_conversion_verified'] and d['ipe_ltm_large_positive_signed_delta_fixed']
    assert not d['ipe_ltm_tmc_gain_sampling_verified'] and not d['ipe_ltm_full_factory_numeric_math_verified'] and not d['ipe_ltm_runtime_submission_enabled']
validation=dict(stage=409,changed_links_syntax_json_checked=True,entrypoint_size_limits_kept=True,
    tested_math_sources_current_hashes_match=True,kernel406_clean_unchanged=True,
    target_sampled_gain_conversion_and_blend_checked=True,source_packers_and_native_typed_luts_checked=True,
    signed_positive_delta_failure_retained_and_corrected=True,old407_and408_records_preserved=True,
    synthetic_gain_and_mix_not_claimed_factory_tmc_outputs=True,no_new_device_epoch_claimed=True,
    private_sources_tables_asm_outputs_not_exported=True,last_device_stage=406,
    previous_goal_turn_classification='progress:408 target Face smoothing and curve phase ordering',
    current_goal_turn_classification='progress:409 target ADRC conversion blend LUT and positive signed delta correction',
    full_goal_kept_active=True,passed=True)
(HERE/'documentation-validation.json').write_text(json.dumps(validation,indent=2)+'\n');selected.append(Path('reference/kernel409/documentation-validation.json'));selected=sorted(set(selected))
repo=Path('/home/cy122/edk2-samurai/repo');mirror=repo/'Platform/Realme/sm8150';git=lambda *args:subprocess.check_output(['git','-C',str(repo),*args])
assert git('rev-parse','HEAD').decode().strip()=='52cc3a87fb77eef8d3727347112e3155b1692688','Inspect changed mirror HEAD'
staged_before=git('diff','--cached','--binary');paths=[]
for relative in selected:
    target=mirror/relative;data=export.public_bytes(ROOT,relative);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);assert target.read_bytes()==data;paths.append(str(Path('Platform/Realme/sm8150')/relative))
subprocess.run(['git','-C',str(repo),'diff','--check','--',*paths],check=True);subprocess.run(['git','-C',str(repo),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(repo),'commit','--only','-m','camera: port sampled ADRC LTM conversion and correct signed packing boundary','--',*paths],check=True)
assert git('diff','--cached','--binary')==staged_before and not git('diff','HEAD','--',*paths)
receipt=dict(stage=409,local_commit=git('rev-parse','HEAD').decode().strip(),files=len(paths),only_checkpoint_paths_committed=True,
    unrelated_index_preserved=True,public_export_used=True,pushed=False,pull_request_created=False,phone_accessed=False,last_device_stage=406,passed=True)
(P/'local-mirror-validation-private.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
