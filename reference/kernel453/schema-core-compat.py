"""Audit exact-tree subdev release callback compatibility; export the core fix."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import re
import subprocess

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('schema_core_storage449', HERE.parent / 'kernel449/storage.py')
storage = importlib.util.module_from_spec(spec); spec.loader.exec_module(storage)
build = storage.mount.mounted_build()
source = build.parent / 'source354'
private = Path('/mnt/e/edk2-samurai-out/kernel453/schema')
env = dict(os.environ, GIT_OPTIONAL_LOCKS='0')

def git(*args):
    return subprocess.check_output(['git', '-C', str(source), *args], env=env)

def body(text, start):
    brace = text.index('{', start)
    end = brace + 1; depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}'); end += 1
    return text[start:end]

files = git('grep', '-l', 'struct v4l2_subdev_internal_ops', '--', '*.c').decode().splitlines()
rows = []; callbacks = {}
for name in files:
    text = (source / name).read_text()
    for match in re.finditer(r'\bstruct v4l2_subdev_internal_ops\s+(\w+)\s*=\s*\{', text):
        init = body(text, match.start())
        release = re.search(r'\.release\s*=\s*(\w+)', init)
        if not release:
            continue
        callback = release[1]
        definition = re.search(r'(?m)^[\w\s*]+\b' + re.escape(callback) + r'\([^;]*?\)\s*\{', text)
        assert definition, (name, callback)
        function = body(text, definition.start()).strip()
        callbacks[name + ':' + callback] = function
        rows.append(dict(path=name, ops=match[1], release=callback,
                         line=text[:definition.start()].count('\n') + 1,
                         body_sha256=hashlib.sha256(function.encode()).hexdigest(),
                         directly_mentions_devnode='devnode' in function))
(private / 'subdev-release-callbacks-private.json').write_text(json.dumps(callbacks, indent=2) + '\n')
patch = (private / 'v4l2-device-release-order-candidate-private.patch').read_bytes()
public_patch = HERE / '0064-media-v4l2-core-clear-devnode-before-subdev-release.patch'
public_patch.write_bytes(patch)
check = subprocess.run(['git', '-C', str(source), 'apply', '--check', str(public_patch)], env=env, capture_output=True)
(private / 'core-apply-check-private.log').write_bytes(check.stdout + check.stderr)
assert check.returncode == 0
report = dict(stage=453, scope='static exact-tree release callback scan, not runtime compatibility test',
              current_source_head=git('rev-parse', 'HEAD').decode().strip(),
              c_files_containing_internal_ops_type=len(files), explicit_release_initializers=len(rows),
              callbacks=rows, any_callback_directly_mentions_devnode=any(r['directly_mentions_devnode'] for r in rows),
              callback_bodies_need_transitive_review=False,
              manual_helper_review='v4l2_get_subdevdata reads sd->dev_priv; other callback only container_of and kfree',
              current_tree_only_no_out_of_tree_or_runtime_claim=True, patch=public_patch.name,
              patch_sha256=hashlib.sha256(patch).hexdigest(), current_tree_apply_check_exit=check.returncode,
              source_or_index_modified=False, core_kernel_built_or_booted=False,
              sdk_or_phone_accessed=False)
(HERE / 'schema-core-compatibility.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
