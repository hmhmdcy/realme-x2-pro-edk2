"""Offline finite preparation checks. No target/SDK/transport entry point."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import runpy
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    guard_spec = importlib.util.spec_from_file_location('guard482', HERE.parent / 'kernel284/storage.py')
    guard = importlib.util.module_from_spec(guard_spec)
    guard_spec.loader.exec_module(guard)
    guard.mounted_build()
    for path in HERE.glob('*.py'):
        ast.parse(path.read_text())
    callback = runpy.run_path(str(HERE / 'default-probe.py'))
    audit = runpy.run_path(str(HERE / 'probe-log-audit.py'))
    tools = {
        'pipeline-fixture': PRIVATE / 'kernel449/pipeline-fixture-long',
        'gst-sustained': PRIVATE / 'kernel449/gst-sustained',
        'pipeline-smoke': PRIVATE / 'kernel440/pipeline-smoke',
        'user-launcher.py': HERE.parent / 'kernel449/user-launcher.py',
    }
    assert all(sha(path) == callback['TOOLS'][name] for name, path in tools.items())
    assert sha(HERE.parent / 'kernel440/recipes/samurai-camera-config/configuration.yaml') == callback['GENERIC_CONFIGURATION']
    original = PRIVATE / 'kernel440/install-collected-r2'
    cases = []
    for name in ['gst-imx471.log', 'gst-imx319.log', 'gst-s5k3m5.log', 'gst-s5kgw1.log', 'raw-raw.log', 'raw-dual.log']:
        path = original / name
        observations, queues, receipt, history, numeric, numeric_receipts, revision = audit['audit_history'](path.read_text())
        cases.append(dict(name=name, sha256=sha(path), observations=len(observations), queues=len(queues),
                          history=history, numerical_commits=revision, passed=True))
    source = Path(json.loads((HERE.parent / 'kernel473/source-state.json').read_text())['source'])
    recipe = json.loads((HERE.parent / 'kernel475/source-recipe-validation.json').read_text())
    hashes = {row['path']: row['after_sha256'] for row in recipe['changed_source_files']}
    selected = ['src/libcamera/pipeline/camss-vfe/camss_vfe.cpp', 'src/ipa/camss-vfe/camss.cpp']
    assert all(sha(source / name) == hashes[name] for name in selected)
    config = (source / 'output/config.h').read_text()
    for definition in ['#define IPA_MODULE_DIR "/usr/lib/libcamera/ipa"',
                       '#define IPA_PROXY_DIR "/usr/libexec/libcamera"',
                       '#define LIBCAMERA_SYSCONF_DIR "/etc/libcamera"']:
        assert definition in config
    report = dict(stage=482, passed=True, scope='offline callback preparation and cached history protocol only',
        source_files={p.name: sha(p) for p in HERE.iterdir() if p.suffix in ['.py', '.md']},
        tools={name: dict(path=str(path), sha256=sha(path)) for name, path in tools.items()},
        source_hashes={name: sha(source / name) for name in selected},
        installed_lookup_config_sha256=sha(source / 'output/config.h'),
        generic_configuration_sha256=callback['GENERIC_CONFIGURATION'],
        normal_policy='valid signature and native app==IPA PID; signature fallback is failure',
        callback_import_has_no_target_actions=True, cached_history_cases=cases,
        cached_regression_not475_hardware_proof=True, full_callback_executed=False,
        cases_per_phase=7, gst_frames_each=32, raw_target_frames_each=6,
        phases=['forward-first', 'forward-final'],
        no_ssh=True, no_sdk=True, no_build=True, no_upload=True, no_target_execution=True)
    (HERE / 'preparation-validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
