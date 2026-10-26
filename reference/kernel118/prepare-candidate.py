from pathlib import Path
import subprocess,hashlib,difflib,json
old=Path('/home/cy122/pmos-samurai-kernel115')
stage=Path('/home/cy122/pmos-samurai-kernel118')
out=Path('/mnt/e/edk2-samurai-out/kernel118')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel118')
assert stage.is_mount() and sorted(p.name for p in stage.iterdir())==['lost+found']
assert hashlib.sha256((old/'kernel/arch/arm64/boot/Image').read_bytes()).hexdigest()=='66e749a8e9902c5675af736706c193b645d7e1ab49f71980e5c0c652db45bfa2'
out.mkdir(mode=0o700,exist_ok=True)
for name in ['kernel','initramfs']:
    subprocess.run(['cp','-a','--reflink=auto',str(old/name),str(stage/name)],check=True)
k=stage/'kernel'
config=k/'.config'
t=config.read_text()
assert t.count(str(old/'initramfs'))==1
config.write_text(t.replace(str(old/'initramfs'),str(stage/'initramfs')))
p=k/'drivers/gpu/drm/msm/disp/dpu1/dpu_hw_ctl.c'
before=p.read_text()
start=before.index('static u32 dpu_hw_ctl_poll_reset_status(')
end=before.index('\n}',start)+2
part=before[start:end]
assert part.count('\treturn status;')==1 and 'usleep_range(20, 50)' in part
part=part.replace('\treturn status;','''\t/* A delayed wakeup can cross the deadline after hardware cleared
\t * reset. Sample again rather than return the value from before sleep.
\t */
\treturn DPU_REG_READ(c, CTL_SW_RESET) & BIT(0);''')
after=before[:start]+part+before[end:]
p.write_text(after)
diff=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/drivers/gpu/drm/msm/disp/dpu1/dpu_hw_ctl.c',tofile='b/drivers/gpu/drm/msm/disp/dpu1/dpu_hw_ctl.c'))
(ref/'ctl-reset-final-read.patch').write_text(diff)
subprocess.run(['git','diff','--check','--','drivers/gpu/drm/msm/disp/dpu1/dpu_hw_ctl.c'],cwd=k,check=True)
report=dict(candidate=118,base=115,one_dpu_poll_function_changed=True,timeout_us_unchanged=2000,final_mmio_read_added=True,all_handoff_and_iommu_guards_preserved=True,not_deployed=True,goal_complete=False)
for folder in [out,ref]: (folder/'candidate-preparation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
