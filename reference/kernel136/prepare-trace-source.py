from pathlib import Path
import difflib
import hashlib
import json
import os
import runpy
import shutil
import subprocess

repo = Path('/mnt/e/RealmeX2Pro edk2')
ref = repo / 'reference/kernel136'
out = Path('/mnt/e/edk2-samurai-out/kernel136')
stage = Path('/home/cy122/pmos-samurai-kernel136')
assert os.geteuid() == 0 and not stage.exists()
assert shutil.disk_usage('/mnt/c').free > 6 * 1024**3
runpy.run_path(str(repo / 'reference/kernel118/ensure-build-volume.py'))
base = Path('/home/cy122/pmos-samurai-kernel118/power132')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(base / 'kernel/arch/arm64/boot/Image') == '2b903902f9f5ab64bd663753fb1c6c4e925aa661881e7aac1cf5481657a72537'
baseline_diff = subprocess.check_output(['git', '-C', str(base / 'kernel'), 'diff', '--binary'])
(out / 'baseline132-source-private.patch').write_bytes(baseline_diff)
stage.mkdir(mode=0o700)
for name in ['kernel', 'initramfs']:
    subprocess.run(['cp', '-a', str(base / name), str(stage / name)], check=True, timeout=300)
    print('K136_ISOLATED_C_SOURCE_COPY_COMPLETE', name, flush=True)
k = stage / 'kernel'
assert subprocess.check_output(['git', '-C', str(k), 'diff', '--binary']) == baseline_diff
changes = {}
header = 'drivers/gpu/drm/msm/msm_gpu_trace.h'
old = (k / header).read_text()
anchor = 'TRACE_EVENT(msm_gpu_submit,\n'
events = '''/* Software mapping changes and queued page-table switches, disabled by default. */
TRACE_EVENT(msm_gpu_vm_update,
\tTP_PROTO(pid_t pid, u64 ttbr, bool managed, const char *op,
\t\t u64 iova, u64 range, int queue_id, int ret),
\tTP_ARGS(pid, ttbr, managed, op, iova, range, queue_id, ret),
\tTP_STRUCT__entry(
\t\t__field(pid_t, pid)
\t\t__field(u64, ttbr)
\t\t__field(bool, managed)
\t\t__string(op, op)
\t\t__field(u64, iova)
\t\t__field(u64, range)
\t\t__field(int, queue_id)
\t\t__field(int, ret)
\t),
\tTP_fast_assign(
\t\t__entry->pid = pid;
\t\t__entry->ttbr = ttbr;
\t\t__entry->managed = managed;
\t\t__assign_str(op);
\t\t__entry->iova = iova;
\t\t__entry->range = range;
\t\t__entry->queue_id = queue_id;
\t\t__entry->ret = ret;
\t),
\tTP_printk("pid=%d ttbr=%016llx managed=%d op=%s iova=%016llx range=%016llx queue=%d ret=%d",
\t\t__entry->pid, __entry->ttbr, __entry->managed, __get_str(op),
\t\t__entry->iova, __entry->range, __entry->queue_id, __entry->ret)
);

TRACE_EVENT(msm_gpu_vm_switch_enqueue,
\tTP_PROTO(pid_t pid, u32 ringid, u32 seqno, u32 old_ctx, u32 new_ctx, u64 ttbr),
\tTP_ARGS(pid, ringid, seqno, old_ctx, new_ctx, ttbr),
\tTP_STRUCT__entry(
\t\t__field(pid_t, pid)
\t\t__field(u32, ringid)
\t\t__field(u32, seqno)
\t\t__field(u32, old_ctx)
\t\t__field(u32, new_ctx)
\t\t__field(u64, ttbr)
\t),
\tTP_fast_assign(
\t\t__entry->pid = pid;
\t\t__entry->ringid = ringid;
\t\t__entry->seqno = seqno;
\t\t__entry->old_ctx = old_ctx;
\t\t__entry->new_ctx = new_ctx;
\t\t__entry->ttbr = ttbr;
\t),
\tTP_printk("pid=%d ring=%d seqno=%u old_ctx=%u new_ctx=%u ttbr=%016llx",
\t\t__entry->pid, __entry->ringid, __entry->seqno,
\t\t__entry->old_ctx, __entry->new_ctx, __entry->ttbr)
);

'''
assert old.count(anchor) == 1
new = old.replace(anchor, events + anchor)
(k / header).write_text(new)
changes[header] = (old, new)
name = 'drivers/gpu/drm/msm/msm_gem_vma.c'
old = (k / name).read_text()
anchor = '#include "msm_mmu.h"\n'
assert old.count(anchor) == 1
new = old.replace(anchor, anchor + '#include "msm_gpu_trace.h"\n')
anchor = 'static void\nvm_unmap_op(struct msm_gem_vm *vm, const struct msm_vm_unmap_op *op)\n'
helper = '''static void vm_trace_update(struct msm_gem_vm *vm, const char *op,
\t\t\t    u64 iova, u64 range, int queue_id, int ret)
{
\tphys_addr_t ttbr;
\tu32 asid;

\tif (!trace_msm_gpu_vm_update_enabled())
\t\treturn;
\tif (msm_iommu_pagetable_params(vm->mmu, &ttbr, &asid))
\t\treturn;

\ttrace_msm_gpu_vm_update(pid_nr(vm->pid), ttbr, vm->managed, op,
\t\t\t       iova, range, queue_id, ret);
}

'''
assert new.count(anchor) == 1
new = new.replace(anchor, helper + anchor)
anchor = '\tvm->mmu->funcs->unmap(vm->mmu, op->iova, op->range);\n'
assert new.count(anchor) == 1
new = new.replace(anchor, anchor + '\tvm_trace_update(vm, reason, op->iova, op->range, op->queue_id, 0);\n')
anchor = '''\tvm_log(vm, "map", op->iova, op->range, op->queue_id);

\treturn vm->mmu->funcs->map(vm->mmu, op->iova, op->sgt, op->offset,
\t\t\t\t   op->range, op->prot);
'''
replacement = '''\tint ret;

\tvm_log(vm, "map", op->iova, op->range, op->queue_id);

\tret = vm->mmu->funcs->map(vm->mmu, op->iova, op->sgt, op->offset,
\t\t\t\top->range, op->prot);
\tvm_trace_update(vm, "map", op->iova, op->range, op->queue_id, ret);
\treturn ret;
'''
assert new.count(anchor) == 1
new = new.replace(anchor, replacement)
(k / name).write_text(new)
changes[name] = (old, new)
name = 'drivers/gpu/drm/msm/adreno/a6xx_gpu.c'
old = (k / name).read_text()
anchor = '\t/* Execute the table update */\n'
assert old.count(anchor) == 1
new = old.replace(anchor, '''\ttrace_msm_gpu_vm_switch_enqueue(pid_nr(submit->pid), ring->id,
\t\t\t\t       submit->seqno, ring->cur_ctx_seqno,
\t\t\t\t       ctx->seqno, ttbr);

''' + anchor)
(k / name).write_text(new)
changes[name] = (old, new)
patch = ''.join(''.join(difflib.unified_diff(a.splitlines(True), b.splitlines(True),
               fromfile='a/' + name, tofile='b/' + name)) for name, (a, b) in changes.items())
(ref / 'gpu-vm-tracepoints.patch').write_text(patch)
config = k / '.config'
old_config = config.read_text()
assert str(base / 'initramfs') in old_config
config.write_text(old_config.replace(str(base / 'initramfs'), str(stage / 'initramfs')))
assert subprocess.check_output(['git', '-C', str(base / 'kernel'), 'diff', '--binary']) == baseline_diff
assert sha(base / 'kernel/arch/arm64/boot/Image') == '2b903902f9f5ab64bd663753fb1c6c4e925aa661881e7aac1cf5481657a72537'
report = dict(stage=136, base_software_generation=132, isolated_source_copy=True,
              changed_gpu_source_files=list(changes), changed_config_only_initramfs_path=True,
              device_tree_charger_and_display_sources_unchanged=True,
              tracepoints_disabled_by_default=True, cache_commands_and_timing_unchanged=True,
              vm_history_for_legacy_managed_vms=True, gpu_fix_accepted=False,
              baseline132_preserved=True, goal_complete=False)
(ref / 'trace-source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('K136_LEGACY_VM_TRACE_SOURCE_READY_STABLE132_UNCHANGED', flush=True)
