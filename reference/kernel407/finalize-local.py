"""Save the checked portable LTM primitives and scoped checkpoint locally."""
from pathlib import Path
import ast, importlib.util, json, subprocess
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P = Path('/mnt/e/edk2-samurai-out/kernel407')

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

reports = {name: json.loads((HERE / (name + '-validation.json')).read_text())
           for name in ['curves', 'float-comparison', 'kernel-luts']}
assert all(r['passed'] for r in reports.values())
assert not json.loads((HERE / 'curves-r1-validation.json').read_text())['passed']
assert reports['curves']['valid_cases'] == reports['curves']['original_hal_cases'] == 6549
assert reports['curves']['factory_regions'] == 2135
assert sum(r['roots'] for r in reports['curves']['original_factory_regions']) == 149
assert all(not r['original_source_packed_different_bytes'] for r in reports['curves']['architectures'])
assert reports['kernel-luts']['compared_bytes'] == 2514816 and not reports['kernel-luts']['different_bytes']
assert all(g['host_hal_float_different_bytes'] == g['host_arm_float_different_bytes'] == 0
           for g in reports['float-comparison']['groups'].values())
state = json.loads((HERE / 'source-state.json').read_text())
storage = module('storage284', HERE.parent / 'kernel284/storage.py')
source = storage.mounted_build().parent / 'source354'
assert subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip() == state['commit']
assert not subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain'])
assert not state['phone_accessed'] and not state['installed']
assert state['source_unchanged_from406'] and state['last_device_evidence_stage'] == 406
index = module('session_index', ROOT / 'linux-port/scripts/generate-session-index.py')
(ROOT / 'sessions/INDEX.md').write_text(index.render(ROOT))
check = module('docs_check', ROOT / 'linux-port/scripts/docs-health-check.py')
export = check.public_module(ROOT)
selected = [p.relative_to(ROOT) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
selected += [Path(p) for p in ['NEXT-SESSION.md', 'NEXT-SESSION-PROMPT.md', 'DOCS-INDEX.md', 'sessions/INDEX.md', 'archive/NEXT-SESSION-through406-2026-10-21.md', 'linux-port/camera/deployment-lock.json', 'linux-port/camera/kernel/source-lock.json', 'linux-port/camera/README.md', 'linux-port/camera/kernel/README.md', 'linux-port/docs/HARDWARE-STATUS.md']]
for relative in selected:
    if relative.suffix == '.md':
        assert not check.link_errors(ROOT, str(relative)), (relative, check.link_errors(ROOT, str(relative)))
    if relative.suffix == '.py':
        ast.parse((ROOT / relative).read_text())
    if relative.suffix == '.json':
        json.loads((ROOT / relative).read_text())
limits = check.load_manifest(ROOT)['size_limits']
for p in ['NEXT-SESSION.md', 'NEXT-SESSION-PROMPT.md', 'DOCS-INDEX.md']:
    assert (ROOT / p).stat().st_size <= limits[p], (p, (ROOT / p).stat().st_size, limits[p])
for relative in ['linux-port/camera/deployment-lock.json', 'linux-port/camera/kernel/source-lock.json']:
    d = json.loads((ROOT / relative).read_text())
    assert d['latest_work_stage'] == 407
    assert d['current_device_revalidated_stage'] == d['ipe_latest_hardware_stage'] == 406
    assert not d['latest_stage_phone_accessed'] and not d['latest_stage_device_mutated']
    assert d['ipe_ltm_curve_primitives_verified'] and not d['ipe_ltm_curve_product_integrated']
    assert not d['ipe_ltm_full_factory_numeric_math_verified'] and not d['ipe_ltm_runtime_submission_enabled']
validation = dict(stage=407, changed_links_syntax_json_checked=True, entrypoint_size_limits_kept=True,
                  source406_clean_and_unchanged=True, original_source_and_hal_curve_primitives_checked=True,
                  all_factory_regions_and_nonzero_native_lut_path_checked=True,
                  first_lce_packing_failure_retained=True,
                  powf_provider_and_oem_adrc_boundaries_explicit=True,
                  no_new_device_epoch_claimed=True, last_device_stage=406,
                  private_original_sources_tables_outputs_not_exported=True,
                  previous_goal_turn_classification='progress:406 physical LTM correction and local checkpoint commit',
                  current_goal_turn_classification='progress:407 portable original curve primitives and native LUT connection',
                  full_goal_kept_active=True, passed=True)
(HERE / 'documentation-validation.json').write_text(json.dumps(validation, indent=2) + '\n')
selected.append(Path('reference/kernel407/documentation-validation.json'))
selected = sorted(set(selected))
repo = Path('/home/cy122/edk2-samurai/repo')
mirror = repo / 'Platform/Realme/sm8150'
git = lambda *args: subprocess.check_output(['git', '-C', str(repo), *args])
assert git('rev-parse', 'HEAD').decode().strip() == '33e0e18e3c8b5b244fc4ef5be3cf12cdba144eac', 'Inspect changed mirror HEAD'
staged_before = git('diff', '--cached', '--binary')
paths = []
for relative in selected:
    target = mirror / relative
    data = export.public_bytes(ROOT, relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    assert target.read_bytes() == data
    paths.append(str(Path('Platform/Realme/sm8150') / relative))
subprocess.run(['git', '-C', str(repo), 'diff', '--check', '--', *paths], check=True)
subprocess.run(['git', '-C', str(repo), 'add', '--', *paths], check=True)
subprocess.run(['git', '-C', str(repo), 'commit', '--only', '-m', 'camera: port LTM curve treatment attenuation and signed table generation', '--', *paths], check=True)
assert git('diff', '--cached', '--binary') == staged_before
assert not git('diff', 'HEAD', '--', *paths)
receipt = dict(stage=407, local_commit=git('rev-parse', 'HEAD').decode().strip(), files=len(paths),
               only_checkpoint_paths_committed=True, unrelated_index_preserved=True,
               public_export_used=True, pushed=False, pull_request_created=False,
               phone_accessed=False, last_device_stage=406, passed=True)
(P / 'local-mirror-validation-private.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
