"""Check corrected fixed LTM evidence and save a scoped local mirror commit."""
from pathlib import Path
import ast, importlib.util, json, subprocess
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
P = Path('/mnt/e/edk2-samurai-out/kernel406')

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

for name in ['ip-enable', 'pixels', 'current-state', 'intree-build', 'test-intree-build', 'client-build']:
    assert json.loads((HERE / (name + '-validation.json')).read_text())['passed'], name
assert not json.loads((HERE / 'pixels-validation-r1.json').read_text())['passed']
runtime = json.loads((HERE / 'runtime-validation.json').read_text())
assert runtime['state']['passed'] and runtime['state']['terminal']
assert not any(runtime[key] for key in ['worker_live', 'client_live', 'collector_live'])
assert not json.loads((HERE / 'intree-build-validation.json').read_text())['diagnostics']
storage = module('storage284', HERE.parent / 'kernel284/storage.py')
source = storage.mounted_build().parent / 'source354'
state = json.loads((HERE / 'source-state.json').read_text())
assert not state['installed'] and state['phone_accessed']
assert state['hardware_fixed_diagnostics_verified'] and state['normal395_393_restored']
assert subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip() == state['commit']
assert not subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain'])
for relative in state['changed']:
    assert (source / relative).read_bytes() == (P / (Path(relative).name + '.proposed')).read_bytes()
index = module('session_index', ROOT / 'linux-port/scripts/generate-session-index.py')
(ROOT / 'sessions/INDEX.md').write_text(index.render(ROOT))
check = module('docs_check', ROOT / 'linux-port/scripts/docs-health-check.py')
export = check.public_module(ROOT)
selected = [p.relative_to(ROOT) for p in HERE.iterdir() if p.is_file()]
selected += [Path(p) for p in ['WORKING-BOUNDARIES.md', 'NEXT-SESSION.md', 'NEXT-SESSION-PROMPT.md', 'DOCS-INDEX.md', 'sessions/INDEX.md', 'archive/NEXT-SESSION-through405-2026-10-21.md', 'linux-port/camera/deployment-lock.json', 'linux-port/camera/kernel/source-lock.json', 'linux-port/camera/README.md', 'linux-port/camera/kernel/README.md', 'linux-port/docs/HARDWARE-STATUS.md']]
for p in selected:
    if p.suffix == '.md':
        assert not check.link_errors(ROOT, str(p)), (p, check.link_errors(ROOT, str(p)))
    if p.suffix == '.py':
        ast.parse((ROOT / p).read_text())
    if p.suffix == '.json':
        json.loads((ROOT / p).read_text())
limits = check.load_manifest(ROOT)['size_limits']
for p in ['NEXT-SESSION.md', 'NEXT-SESSION-PROMPT.md', 'DOCS-INDEX.md']:
    assert (ROOT / p).stat().st_size <= limits[p], (p, (ROOT / p).stat().st_size, limits[p])
for relative in ['linux-port/camera/deployment-lock.json', 'linux-port/camera/kernel/source-lock.json']:
    d = json.loads((ROOT / relative).read_text())
    assert d['latest_work_stage'] == d['current_device_revalidated_stage'] == d['ipe_latest_hardware_stage'] == 406
    assert d['latest_stage_phone_accessed'] and d['ipe_ltm_hardware_fixed_diagnostics_verified']
    assert d['ipe_ltm_hardware_verified'] and d['ipe_ltm_full_pass_ip_from_explicit_request']
    assert not d['ipe_ltm_runtime_submission_enabled'] and not d['ipe_ltm_product_default_enabled']
    assert not d['ipe_ltm_full_factory_numeric_math_verified'] and not d['ipe_ltm_data_collection_statistics_verified']
validation = dict(stage=406, changed_links_syntax_json_checked=True, entrypoint_size_limits_kept=True,
                 source_clean_and_matches_tested_proposal=True, explicit_ip_enable_correction=True,
                 r1_pixel_failure_retained=True, r2_fixed52_pixels_passed=True,
                 formal395_393_restored_and_four_cameras48_passed=True,
                 fixed_diagnostics_not_claimed_as_full_calibration=True,
                 private_original_sources_tables_commands_images_not_exported=True,
                 previous_goal_turn_classification='progress:405 typed LTM request ownership implementation',
                 current_goal_turn_classification='progress:406 physical LTM diagnostics and full-pass IP correction',
                 full_goal_kept_active=True, passed=True)
(HERE / 'documentation-validation.json').write_text(json.dumps(validation, indent=2) + '\n')
selected.append(Path('reference/kernel406/documentation-validation.json'))
selected = sorted(set(selected))
repo = Path('/home/cy122/edk2-samurai/repo')
mirror = repo / 'Platform/Realme/sm8150'
git = lambda *args: subprocess.check_output(['git', '-C', str(repo), *args])
assert git('rev-parse', 'HEAD').decode().strip() == '0143764263bd92e4cc08c414fe2e9dcaf1772ef1', 'Inspect changed mirror HEAD'
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
subprocess.run(['git', '-C', str(repo), 'commit', '--only', '-m', 'camera: verify fixed LTM pixels and correct explicit full-pass IP enable', '--', *paths], check=True)
assert git('diff', '--cached', '--binary') == staged_before
assert not git('diff', 'HEAD', '--', *paths)
receipt = dict(stage=406, local_commit=git('rev-parse', 'HEAD').decode().strip(), files=len(paths),
               only_checkpoint_paths_committed=True, unrelated_index_preserved=True,
               public_export_used=True, pushed=False, pull_request_created=False,
               formal395_393_restored=True, passed=True)
(P / 'local-mirror-validation-private.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
