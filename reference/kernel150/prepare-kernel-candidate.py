"""Generate and compile a scoped compatibility proposal without editing the kernel tree."""
from pathlib import Path
import difflib, hashlib, json, shlex, shutil, subprocess

kernel = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel150')
output = Path('/mnt/e/edk2-samurai-out/kernel150/compile')
output.mkdir(parents=True, exist_ok=True)
relative = 'drivers/gpu/drm/msm/adreno/adreno_gpu.c'
source = kernel/relative
old = source.read_text()
changes = [
    ('#include <linux/of_reserved_mem.h>\n', '#include <linux/of.h>\n#include <linux/of_reserved_mem.h>\n'),
    ('static bool\nvalid_per_process_vm(', '''/* Local compatibility policy, scoped to the handset with reproduced faults.
 * Kernel-managed A640 BO allocations already use 64 KiB alignment.
 * Optional userspace address allocation cannot enforce that alignment.
 */
static bool adreno_kernel_iova_only(struct msm_gpu *gpu)
{
\treturn adreno_is_a640(to_adreno_gpu(gpu)) &&
\t\tof_machine_is_compatible("realme,samurai");
}

static bool
valid_per_process_vm('''),
    ('\tcase MSM_PARAM_VA_START:\n', '''\tcase MSM_PARAM_VA_START:
\t\tif (adreno_kernel_iova_only(gpu))
\t\t\treturn -EOPNOTSUPP;
'''),
    ('\tcase MSM_PARAM_EN_VM_BIND: {\n', '''\tcase MSM_PARAM_EN_VM_BIND: {
\t\tif (adreno_kernel_iova_only(gpu))
\t\t\treturn -EOPNOTSUPP;

'''),
]
new = old
for before, after in changes:
    assert new.count(before) == 1, before
    new = new.replace(before, after)
patch = ref/'a640-kernel-iova-compat.patch'
patch.write_text('''Subject: [LOCAL PROPOSAL] drm/msm: use kernel-managed IOVA on samurai A640

Requires the existing A640 64 KiB kernel-managed IOVA alignment fix.
Disable VM_BIND opt-in and VA_START capability discovery on samurai only.
Stock Mesa 26.2.4 falls back to GET_IOVA; rejecting VM_BIND alone is
insufficient because Mesa otherwise retains its SET_IOVA allocator.
Keep VA_SIZE available for Gallium's address-space-aware memory budget.

This trades sparse binding, address capture/replay, and lazy allocation
for compatibility. It is not a full-feature hardware erratum fix and
has not been deployed. See the accompanying research and receipts.

---

diff --git a/'''+relative+' b/'+relative+'\n'+''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
    fromfile='a/'+relative, tofile='b/'+relative)))
candidate = output/relative
candidate.parent.mkdir(parents=True, exist_ok=True)
candidate.write_text(old)
subprocess.run(['git', 'apply', '--check', str(patch)], cwd=output, check=True)
subprocess.run(['git', 'apply', str(patch)], cwd=output, check=True)
assert candidate.read_text() == new
saved = (source.parent/'.adreno_gpu.o.cmd').read_text().splitlines()[0].split(' := ', 1)[1]
args = shlex.split(saved)
assert ';' not in args and '&&' not in args
for i, argument in enumerate(args):
    if argument.startswith('-Wp,-MMD,'):
        args[i] = '-Wp,-MMD,'+str(output/'adreno_gpu.d')
    elif argument == relative:
        args[i] = str(candidate)
    elif argument == relative[:-2]+'.o':
        args[i] = str(output/'adreno_gpu.o')
args += ['-Werror', '-Wmissing-prototypes', '-Wmissing-declarations', '-Wextra',
         '-I'+str(source.parent), '-Idrivers/gpu/drm/msm']
with (output/'compile.log').open('wb') as log:
    completed = subprocess.run(args, cwd=kernel, stdout=log, stderr=subprocess.STDOUT)
report = dict(kernel_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=kernel, text=True).strip(),
    original_source_sha256=hashlib.sha256(old.encode()).hexdigest(),
    candidate_source_sha256=hashlib.sha256(new.encode()).hexdigest(),
    patch_applies=True, compile_exit=completed.returncode,
    compile_log_bytes=(output/'compile.log').stat().st_size,
    existing_kernel_source_preserved=source.read_text() == old,
    proposal_deployed=False, full_kernel_build=False, scope='realme,samurai + A640',
    va_size_preserved=True, requires_kernel147_managed_alignment=True)
(ref/'kernel-candidate-validation.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report))
if completed.returncode:
    print((output/'compile.log').read_text()[-5000:])
    raise SystemExit(completed.returncode)
