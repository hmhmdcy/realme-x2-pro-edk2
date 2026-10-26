"""Prove the exact-tree subdev release ordering with a host C counterexample."""
from pathlib import Path
import difflib
import hashlib
import importlib.util
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('schema_pm_storage449', HERE.parent / 'kernel449/storage.py')
storage = importlib.util.module_from_spec(spec); spec.loader.exec_module(storage)
shared = storage.mount.mounted_build()
source = shared.parent / 'kernel453-lens-private/source-view/drivers/media/v4l2-core/v4l2-device.c'
private = Path('/mnt/e/edk2-samurai-out/kernel453/schema')
original = source.read_text()
start = original.index('static void v4l2_subdev_release(')
brace = original.index('{', start); depth = 1; end = brace + 1
while depth:
    depth += (original[end] == '{') - (original[end] == '}'); end += 1
function = original[start:end]
old = '\tif (sd->internal_ops && sd->internal_ops->release)\n\t\tsd->internal_ops->release(sd);\n\tsd->devnode = NULL;'
new = '\tsd->devnode = NULL;\n\tif (sd->internal_ops && sd->internal_ops->release)\n\t\tsd->internal_ops->release(sd);'
assert function.count(old) == 1
patched_function = function.replace(old, new)
patched = original[:start] + patched_function + original[end:]
(private / 'v4l2-device-release-order-candidate-private.c').write_text(patched)
patch = ''.join(difflib.unified_diff(original.splitlines(True), patched.splitlines(True),
                                    fromfile='a/drivers/media/v4l2-core/v4l2-device.c', tofile='b/drivers/media/v4l2-core/v4l2-device.c'))
(private / 'v4l2-device-release-order-candidate-private.patch').write_text(patch)
preamble = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
struct module { unsigned int token; };
struct v4l2_subdev;
struct v4l2_subdev_internal_ops { void (*release)(struct v4l2_subdev *); };
struct v4l2_subdev { bool owner_v4l2_dev; struct module *owner; const struct v4l2_subdev_internal_ops *internal_ops; void *devnode; };
static struct module owner = { 1234 };
static void module_put(struct module *module) { assert(module == &owner); }
static void release_storage(struct v4l2_subdev *sd) { free(sd); }
static const struct v4l2_subdev_internal_ops ops = { .release = release_storage };
'''
main = r'''
int main(void) {
 struct v4l2_subdev *sd = calloc(1,sizeof(*sd));assert(sd);
 sd->owner=&owner;sd->internal_ops=&ops;sd->devnode=sd;
 v4l2_subdev_release(sd);
 return 0;
}
'''
rows = {}
env = dict(os.environ, ASAN_OPTIONS='detect_leaks=1:halt_on_error=1:abort_on_error=0', UBSAN_OPTIONS='halt_on_error=1')
for label, body in [('original', function), ('candidate', patched_function)]:
    harness = private / ('release-order-' + label + '-private.c')
    binary = private / ('release-order-' + label + '-asan')
    harness.write_text(preamble + body + main)
    cc = subprocess.run(['gcc', '-std=gnu11', '-g', '-O0', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                         '-fno-omit-frame-pointer', '-fno-pie', '-no-pie', str(harness), '-o', str(binary)], capture_output=True)
    (private / ('release-order-' + label + '-compile-private.log')).write_bytes(cc.stdout + cc.stderr)
    assert cc.returncode == 0, (cc.stdout + cc.stderr).decode()
    run = subprocess.run([str(binary)], capture_output=True, env=env, timeout=10)
    (private / ('release-order-' + label + '-run-private.log')).write_bytes(run.stdout + run.stderr)
    rows[label] = dict(compile_exit=cc.returncode, run_exit=run.returncode,
                       heap_use_after_free=b'heap-use-after-free' in run.stderr,
                       function_sha256=hashlib.sha256(body.encode()).hexdigest())
assert rows['original']['run_exit'] != 0 and rows['original']['heap_use_after_free']
assert rows['candidate']['run_exit'] == 0 and not rows['candidate']['heap_use_after_free']
assert source.read_text() == original
report = dict(stage=453, scope='exact kernel v4l2_subdev_release C host counterexample, not kernel execution',
              source_path='drivers/media/v4l2-core/v4l2-device.c', source_sha256=hashlib.sha256(original.encode()).hexdigest(),
              original_function_verbatim=True, runs=rows,
              confirmed_callback_can_free_sd_before_framework_devnode_write=True,
              private_patch_moves_devnode_clear_before_callback=True,
              private_patch_kernel_compiled=False, actual_kernel_runtime_or_hardware_tested=False,
              public_driver_or_shared_source_modified=False, sdk_or_phone_accessed=False, passed=True)
(HERE / 'schema-pm-proof.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
