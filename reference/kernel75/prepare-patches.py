from pathlib import Path
import difflib, hashlib, json, shutil, subprocess, tempfile

ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/kernel75')
kernel = Path('/home/cy122/x2pro-linux/linux')
workspace = ref.parents[1]
dpu = 'drivers/gpu/drm/msm/disp/dpu1/'
groups = {
    '0011-drm-msm-sm8150-stalled-boot-and-gpu.patch': [
        dpu+n for n in ('dpu_kms.c','dpu_kms.h','dpu_rm.c','dpu_hw_intf.c','dpu_hw_ctl.c','dpu_hw_ctl.h')
    ] + ['arch/arm64/boot/dts/qcom/sm8150-samurai.dts'],
    '0012-drm-dsi-sofef03f-stock-clock-and-eot.patch': [
        'drivers/gpu/drm/panel/panel-samsung-sofef03f.c',
        'drivers/gpu/drm/msm/dsi/dsi_host.c']
}
descriptions = {
    '0011-drm-msm-sm8150-stalled-boot-and-gpu.patch':
        'drm/msm: abort matched stalled SM8150 boot output and enable samurai A640\n\n'
        'A boot command frame can remain frozen after firmware exits. Stop its\n'
        'TE/trigger and require successful CTL resets covering every stalled INTF\n'
        'before attaching the DPU IOMMU. Track private-object initialization so\n'
        'hardware-init failure finalizes it once. Enable the existing A640/GMU\n'
        'nodes with the signed ZAP path from this handset.\n',
    '0012-drm-dsi-sofef03f-stock-clock-and-eot.patch':
        'drm/dsi: match SOFEF03F stock EOT and noncontinuous clock configuration\n\n'
        'The stock panel does not request EOT append or forced HS clock. Match\n'
        'those flags and explicitly clear inherited controller and PHY forced\n'
        'clock requests for noncontinuous mode. The EOT-only candidate retained\n'
        'colored noise; adding noncontinuous mode produced an optically confirmed\n'
        'clean static-white image. Reboot and color acceptance are recorded in\n'
        'the session evidence, separately from scanout CRCs.\n'
}
baselines = {}
for names in groups.values():
    for n in names:
        if n.endswith('sm8150-samurai.dts'):
            baselines[n] = (out/'dts-before').read_bytes()
        elif (out/(Path(n).name+'.before')).exists():
            baselines[n] = (out/(Path(n).name+'.before')).read_bytes()
        else:
            baselines[n] = (ref.parent/'kernel74'/(Path(n).name+'.after')).read_bytes()
checks = {}
with tempfile.TemporaryDirectory(prefix='k75-apply-') as directory:
    temp = Path(directory)
    for n, raw in baselines.items():
        (temp/n).parent.mkdir(parents=True,exist_ok=True)
        (temp/n).write_bytes(raw)
    for name, names in groups.items():
        diff = ''
        for n in names:
            current = (kernel/n).read_bytes()
            assert current != baselines[n], n
            diff += 'diff --git a/'+n+' b/'+n+'\n'+''.join(difflib.unified_diff(
                baselines[n].decode().splitlines(True), current.decode().splitlines(True),
                'a/'+n, 'b/'+n))
            (ref/(Path(n).name+'.after')).write_bytes(current)
        patch = 'From: hmhmdcy <hmhmdcy@users.noreply.github.com>\nSubject: [PATCH] '+descriptions[name]+'\nSigned-off-by: hmhmdcy <hmhmdcy@users.noreply.github.com>\n\n'+diff
        target = workspace/'linux-port/patches'/name
        target.write_text(patch)
        subprocess.run(['git','apply','--check',str(target)],cwd=temp,check=True)
        subprocess.run(['git','apply',str(target)],cwd=temp,check=True)
        for n in names:
            assert (temp/n).read_bytes() == (kernel/n).read_bytes(), n
        result = subprocess.run(['perl',str(kernel/'scripts/checkpatch.pl'),'--no-tree',str(target)],capture_output=True,text=True)
        (out/(name+'.checkpatch.txt')).write_text(result.stdout+result.stderr)
        checks[name] = dict(exact_apply_pass=True,checkpatch_exit=result.returncode,
                           sha256=hashlib.sha256(target.read_bytes()).hexdigest())
        print(name, 'exact-apply PASS; checkpatch exit', result.returncode)
(out/'patch-validation.json').write_text(json.dumps(checks,indent=2)+'\n')
