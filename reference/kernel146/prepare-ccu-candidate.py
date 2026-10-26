from pathlib import Path
import difflib
import hashlib
import json
import subprocess

k = Path('/home/cy122/pmos-samurai-kernel136/kernel')
out = Path('/mnt/e/edk2-samurai-out/kernel146')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel146')
name = 'drivers/gpu/drm/msm/adreno/a6xx_gpu.c'
source = k / name
old = source.read_text()
assert not (out / 'a6xx-before-private.c').exists()
assert hashlib.sha256((k / 'arch/arm64/boot/Image').read_bytes()).hexdigest() == 'f38c7bf0da64ea39c97233ee981ca2d99df481fb5c1efe94ee9de3863f061163'
block = '''\t/* Invalidate CCU depth and color */
\tOUT_PKT7(ring, CP_EVENT_WRITE, 1);
\tOUT_RING(ring, CP_EVENT_WRITE_0_EVENT(PC_CCU_INVALIDATE_DEPTH));

\tOUT_PKT7(ring, CP_EVENT_WRITE, 1);
\tOUT_RING(ring, CP_EVENT_WRITE_0_EVENT(PC_CCU_INVALIDATE_COLOR));
'''
assert old.count(block) == 1
helper = '''static void a6xx_invalidate_ccu(struct msm_ringbuffer *ring)
{
\tOUT_PKT7(ring, CP_EVENT_WRITE, 1);
\tOUT_RING(ring, CP_EVENT_WRITE_0_EVENT(PC_CCU_INVALIDATE_DEPTH));

\tOUT_PKT7(ring, CP_EVENT_WRITE, 1);
\tOUT_RING(ring, CP_EVENT_WRITE_0_EVENT(PC_CCU_INVALIDATE_COLOR));
}

'''
anchor = 'static void a6xx_submit(struct msm_gpu *gpu, struct msm_gem_submit *submit)\n'
assert old.count(anchor) == 1
new = old.replace(anchor, helper + anchor).replace(block, '''\t/* A640 invalidates its attachment state before retiring this submit. */
\tif (!adreno_is_a640(adreno_gpu))
\t\ta6xx_invalidate_ccu(ring);
''')
start = new.index(anchor)
end = new.index('\nvoid a6xx_emit_set_pseudo_reg', start)
function = new[start:end]
anchor2 = '\tget_stats_counter(ring, REG_A6XX_RBBM_PERFCTR_CP(0),\n\t\trbmemptr_stats(ring, index, cpcycles_end));'
assert function.count(anchor2) == 1
function = function.replace(anchor2, '''\t/*
\t * Retire A640 attachment cache state while this submit's pagetable and
\t * BOs are still valid.  Invalidating only after the next pagetable switch
\t * can make the CCU access the previous submit's attachments in a new VM.
\t */
\tif (adreno_is_a640(adreno_gpu))
\t\ta6xx_invalidate_ccu(ring);

''' + anchor2)
new = new[:start] + function + new[end:]
(out / 'a6xx-before-private.c').write_text(old)
(out / 'a6xx-candidate-private.c').write_text(new)
(out / 'config-before-private').write_bytes((k / '.config').read_bytes())
(out / 'source-diff-before-private.patch').write_bytes(subprocess.check_output(['git', '-C', str(k), 'diff', '--binary']))
patch = ''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
             fromfile='a/' + name, tofile='b/' + name))
(ref / 'a640-ccu-retire-candidate.patch').write_text(patch)
check = subprocess.run(['perl', str(k / 'scripts/checkpatch.pl'), '--no-signoff',
                        '--ignore', 'COMMIT_MESSAGE', str(ref / 'a640-ccu-retire-candidate.patch')], capture_output=True, text=True)
(out / 'checkpatch-private.txt').write_text(check.stdout + check.stderr)
assert check.returncode == 0, check.stdout + check.stderr
report = dict(stage=146, baseline=145, target='Adreno A640', hypothesis_only=True,
              candidate_source_sha256=hashlib.sha256(new.encode()).hexdigest(),
              baseline_source_sha256=hashlib.sha256(old.encode()).hexdigest(),
              changes='Move A640 CCU invalidation after user IBs and before completion fence',
              other_gpu_packet_order_preserved=True, checkpatch_pass=True,
              applied=False, built=False, device_fix_accepted=False)
(ref / 'candidate-preparation.json').write_text(json.dumps(report, indent=2) + '\n')
print('K146_A640_SCOPED_CCU_RETIRE_CANDIDATE_PREPARED')
