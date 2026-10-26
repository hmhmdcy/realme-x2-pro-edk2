"""Make an explicit r32-to-r33 source delta and replay it; no source/build mutation."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil
import subprocess
import storage

HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel475')
volume = storage.mount.mounted_build().parent
base = volume / 'libcamera440-release-r32/src/libcamera-v0.7.2'
core = volume / 'libcamera473-processed-manager-capacity/src/libcamera-v0.7.2'
worker = volume / 'libcamera451-ipa-byte-encoding/src/libcamera-v0.7.2'
work = storage.workspace() / 'source-replay'
assert not work.exists() and not (HERE / 'source-recipe-validation.json').exists()
assert shutil.disk_usage(volume).free > 2 * 1024 ** 3 + 64 * 1024 ** 2
overlay = {
    'utils/codegen/ipc/generators/libcamera_templates/proxy_functions.tmpl',
    'utils/codegen/ipc/generators/libcamera_templates/module_ipa_proxy_worker.cpp.tmpl',
    'include/libcamera/internal/camss_byte_serializer.h',
}
expected = {
    'include/libcamera/ipa/camss.mojom', 'src/ipa/camss-vfe/camss.cpp',
    'src/libcamera/pipeline/camss-vfe/camss_ipe.cpp', 'src/libcamera/pipeline/camss-vfe/camss_ipe.h',
    'src/libcamera/pipeline/camss-vfe/camss_pd10.h', 'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp',
    'src/libcamera/pipeline/camss-vfe/full_ownership_trace.h',
    'src/libcamera/pipeline/camss-vfe/hardware_focus.h', 'src/libcamera/pipeline/camss-vfe/thread_capacity.h',
} | overlay
assert hashlib.sha256((core / 'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp').read_bytes()).hexdigest() == 'be3199aec5ad4c5ffc65043bded6ec85b37a3eeaf20db6087226543fc89ece19'
files = set(overlay)
for root in [base, core]:
    for path in root.rglob('*'):
        rel = path.relative_to(root)
        if rel.parts[0] not in {'output', '.git'} and '__pycache__' not in rel.parts and path.is_file() and not path.is_symlink():
            files.add(rel.as_posix())
changed = {}
for relative in sorted(files):
    a = base / relative
    b = (worker if relative in overlay else core) / relative
    before = a.read_bytes() if a.is_file() else b''
    after = b.read_bytes() if b.is_file() else b''
    if before != after:
        changed[relative] = (before, after)
assert set(changed) == expected, sorted(changed)
patch_name = '0066-camss-r33-processed-ipe-cohort.patch'
patch = HERE / patch_name
assert not patch.exists()
lines = []
for name, (before, after) in changed.items():
    lines.extend(difflib.unified_diff(before.decode().splitlines(True), after.decode().splitlines(True),
                                    fromfile='a/' + name if before else '/dev/null', tofile='b/' + name if after else '/dev/null'))
patch.write_text(''.join(lines))
work.mkdir(parents=True)
for name, (before, after) in changed.items():
    if before:
        target = work / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(before)
for label, extra in [('dry-run', ['--dry-run']), ('apply', [])]:
    run = subprocess.run(['patch', '-p1', '--batch', '--fuzz=0', '-i', str(patch), *extra], cwd=work, capture_output=True)
    log = run.stdout + run.stderr
    (PRIVATE / f'source-replay-{label}-private.log').write_bytes(log)
    assert run.returncode == 0 and b'offset' not in log.lower() and b'fuzz' not in log.lower(), log.decode()
rows = []
for name, (before, after) in changed.items():
    assert (work / name).read_bytes() == after
    rows.append(dict(path=name, before_sha256=hashlib.sha256(before).hexdigest() if before else None,
                     after_sha256=hashlib.sha256(after).hexdigest(), source_stage=451 if name in overlay else 473))
for package in ['libcamera', 'samurai-camera-config']:
    source = HERE.parent / 'kernel440/recipes' / package
    public = HERE / 'recipes' / package
    public.mkdir(parents=True)
    text = (source / 'APKBUILD').read_text()
    if package == 'libcamera':
        assert 'pkgrel=32\n' in text
        text = text.replace('pkgrel=32\n', 'pkgrel=33\n')
        needle = '\t0051-camss-raw-only-pd10-policy.patch\n'
        assert text.count(needle) == 1
        text = text.replace(needle, needle + '\t' + patch_name + '\n')
        at = text.rfind('"')
        text = text[:at] + hashlib.sha512(patch.read_bytes()).hexdigest() + '  ' + patch_name + '\n' + text[at:]
    else:
        assert 'pkgrel=27\n' in text
        text = text.replace('pkgrel=27\n', 'pkgrel=28\n').replace('99990.7.2-r32', '99990.7.2-r33')
    (public / 'APKBUILD').write_text(text)
    materialized = storage.workspace() / 'recipes' / package
    shutil.copytree(source, materialized)
    shutil.copyfile(public / 'APKBUILD', materialized / 'APKBUILD')
    if package == 'libcamera':
        shutil.copyfile(patch, materialized / patch.name)
report = dict(stage=475, baseline_source_stage=440, target_core_source_stage=473, worker_serializer_source_stage=451,
              framework_version='99990.7.2-r33', configuration_version='0.1.0-r28',
              patch=patch_name, patch_sha256=hashlib.sha256(patch.read_bytes()).hexdigest(), changed_source_files=rows,
              compared_source_paths=len(files), zero_fuzz_zero_offset_replay_byte_exact=True,
              full_recipe_source_materialized=True, full_recipe_build_executed=False,
              core_ipa_math_base_and_helper_preserved_from_selected_sources=True,
              private_factory_data_added=False, phone_accessed=False, sdk_bound=False, passed=True)
(HERE / 'source-recipe-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(dict(stage=475, changed_source_files=len(rows), replay_byte_exact=True,
                      recipe_materialized=True, compiled=False, passed=True)), flush=True)
