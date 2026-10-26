"""Check new state wrappers and unchanged devm semantics on actual C bodies."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('api_check_storage449', HERE.parents[1] / 'kernel449/storage.py')
storage = importlib.util.module_from_spec(spec); spec.loader.exec_module(storage)
storage.mount.mounted_build()
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel462/r2')
core = (PRIVATE / 'candidate/drivers/mux/core.c').read_text()
original = (PRIVATE / 'original/drivers/mux/core.c').read_text()
header = (PRIVATE / 'candidate/include/linux/mux/consumer.h').read_text()
sha = lambda s: hashlib.sha256(s.encode()).hexdigest()
def function(text, signature):
    start = text.index(signature); brace = text.index('{', start); end = brace + 1; depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}'); end += 1
    return text[start:end]

private = function(core, 'static struct mux_state *\n__mux_state_get(')
public = function(core, 'struct mux_state *mux_state_get(')
put = function(core, 'void mux_state_put(')
assert private.replace('__mux_state_get(', 'mux_state_get(') == function(original, 'static struct mux_state *\nmux_state_get(')
assert 'static ' + put == function(original, 'static void mux_state_put(')
old_devm = function(original, 'static struct mux_state *__devm_mux_state_get(')
new_devm = function(core, 'static struct mux_state *__devm_mux_state_get(')
assert old_devm.replace('mstate = mux_state_get(', 'mstate = __mux_state_get(') == new_devm
managed = ['static void devm_mux_state_release(', 'struct mux_state *\ndevm_mux_state_get_from_np(',
           'struct mux_state *devm_mux_state_get_optional(', 'struct mux_state *devm_mux_state_get_selected(',
           'struct mux_state *devm_mux_state_get_optional_selected(']
assert all(function(original, name) == function(core, name) for name in managed)
preamble = r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
struct device { int unused; };
struct device_node { int unused; };
struct mux_control { unsigned int references; };
struct mux_state { struct mux_control *mux; unsigned int state; };
#define IS_ERR(p) ((uintptr_t)(p)>=(uintptr_t)-4095)
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define ERR_PTR(e) ((void *)(intptr_t)(e))
static int alloc_fail, lookup_error;
static bool missing;
static unsigned int allocated, freed, lookups;
static struct mux_control control;
static void *alloc(size_t n) { if(alloc_fail)return NULL;allocated++;return calloc(1,n); }
#define kzalloc_obj(v) alloc(sizeof(v))
static void kfree(void *p) { assert(p);freed++;free(p); }
static struct mux_control *mux_get(struct device *d,const char *name,unsigned int *state,bool optional,struct device_node *np) {
 assert(d&&!strcmp(name,"csi-route")&&state&&!optional&&!np);lookups++;
 if(lookup_error)return ERR_PTR(lookup_error);
 if(missing)return NULL;
 control.references++;*state=1;return &control;
}
static void mux_control_put(struct mux_control *m) { assert(m==&control&&m->references);m->references--; }
'''.replace('#include <stdio.h>', '#include <stdio.h>\n#include <string.h>')
main = r'''
int main(void) {
 struct device d={0};struct mux_state *s=mux_state_get(&d,"csi-route");
 assert(!IS_ERR(s)&&s->mux==&control&&s->state==1&&control.references==1);mux_state_put(s);assert(!control.references);
 lookup_error=-517;s=mux_state_get(&d,"csi-route");assert(PTR_ERR(s)==-517&&!control.references);lookup_error=0;
 missing=true;s=mux_state_get(&d,"csi-route");assert(PTR_ERR(s)==-ENOENT&&!control.references);missing=false;
 alloc_fail=1;unsigned int calls=lookups;s=mux_state_get(&d,"csi-route");assert(PTR_ERR(s)==-ENOMEM&&calls==lookups);
 assert(allocated==freed&&allocated==3);puts("MUX_API_C_RESULT cases=4 references_balanced=1 result=0");return 0;
}
'''
attempt = 1
while (PRIVATE / f'mux-api-c-r{attempt}-private.c').exists(): attempt += 1
source = PRIVATE / f'mux-api-c-r{attempt}-private.c'; binary = PRIVATE / f'mux-api-c-r{attempt}-asan'
source.write_text(preamble + '\n' + private + '\n' + public + '\n' + put + '\n' + main)
flags = ['gcc','-std=gnu11','-g','-O1','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie',
         '-Wall','-Wextra','-Werror','-Wno-unused-parameter']
cc = subprocess.run(flags+[str(source),'-o',str(binary)],capture_output=True)
(PRIVATE / f'mux-api-c-r{attempt}-compile-private.log').write_bytes(cc.stdout+cc.stderr)
if cc.returncode:
    print((cc.stdout+cc.stderr).decode()); raise SystemExit(cc.returncode)
env = dict(os.environ,ASAN_OPTIONS='detect_leaks=1:abort_on_error=1',UBSAN_OPTIONS='halt_on_error=1')
run = subprocess.run([str(binary)],capture_output=True,timeout=30,env=env)
(PRIVATE / f'mux-api-c-r{attempt}-run-private.log').write_bytes(run.stdout+run.stderr)
if run.returncode:
    print((run.stdout+run.stderr).decode()); raise SystemExit(run.returncode)
# Build the whole actual consumer header's disabled branch, with only the
# host equivalents of compiler/errno definitions replacing its one include.
disabled = header.replace('#include <linux/compiler.h>', '#include <errno.h>\n#include <stdint.h>\n#define IS_ENABLED(x) 0\n#define __must_check\n#define ERR_PTR(e) ((void *)(intptr_t)(e))\n#define NULL ((void *)0)')
disabled += '\nint main(void) { return (intptr_t)mux_state_get(NULL, NULL) != -EOPNOTSUPP || (intptr_t)devm_mux_state_get(NULL, NULL) != -EOPNOTSUPP; }\n'
disabled_source = PRIVATE / f'mux-disabled-r{attempt}-private.c'; disabled_source.write_text(disabled)
disabled_binary = PRIVATE / f'mux-disabled-r{attempt}'
cc_disabled = subprocess.run(flags+[str(disabled_source),'-o',str(disabled_binary)],capture_output=True)
(PRIVATE / f'mux-disabled-r{attempt}-compile-private.log').write_bytes(cc_disabled.stdout+cc_disabled.stderr)
if cc_disabled.returncode:
    print((cc_disabled.stdout+cc_disabled.stderr).decode()); raise SystemExit(cc_disabled.returncode)
subprocess.run([str(disabled_binary)],check=True,env=env,timeout=30,capture_output=True)
report = dict(stage=462,revision='r2',passed=True,attempt=attempt,core_sha256=sha(core),header_sha256=sha(header),
              unmanaged_wrapper_exact_c_checked=True,unmanaged_four_result_cases=True,
              lookup_and_put_algorithm_identical_to_original=True,
              devm_wrapper_unchanged_except_private_helper_name=True,
              existing_managed_entrypoints_and_release_unchanged=len(managed),
              disabled_consumer_header_with_host_compiler_definitions_compiled=True,
              result=run.stdout.decode().strip(),kernel_of_resolution_or_supplier_lifetime_tested=False,
              old363_missing_new_exports=True,new_image_required=True,phone_or_sdk_accessed=False)
(HERE / 'mux-api-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
