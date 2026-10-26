from pathlib import Path
import difflib,hashlib,json,subprocess
root=Path('/mnt/e/RealmeX2Pro edk2');out=Path('/mnt/e/edk2-samurai-out');k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
before=json.loads((out/'kernel156/source-before-private.json').read_text())
for stage in [157,158]:
    for n,s in json.loads((out/f'kernel{stage}/source-before-private.json').read_text()).items():
        if n not in before:before[n]=s
assert len(before)==14,len(before)
patch='Subject: [PATCH] drm/msm: quiesce firmware DSI and gate panel illumination\n\n'+\
    'On SOFEF03F, stop the inherited host before SM8150 boot CTL cleanup\n'+\
    'and PHY configuration. Defer backlight/followers until DPU pixel TX\n'+\
    'completion, and reset readiness on disable. This is based on kernel154\n'+\
    'including its probe GPIO and host timing fixes.\n\n---\n\n'
names=[]
for n,s in before.items():
    after=(k/n).read_text()
    if s==after:continue
    patch+='diff --git a/'+n+' b/'+n+'\n'
    if s is None:
        patch+='new file mode 100644\n';s='';old='/dev/null'
    else:old='a/'+n
    patch+=''.join(difflib.unified_diff(s.splitlines(True),after.splitlines(True),fromfile=old,tofile='b/'+n));names.append(n)
p=root/'reference/kernel158/display-fix-from154.patch';p.write_text(patch)
r=subprocess.run(['git','apply','--reverse','--check',str(p)],cwd=k,capture_output=True,text=True)
(out/'kernel158/consolidated-patch-check-private.txt').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr
result=dict(baseline_kernel=154,target_kernel=158,modified_files=names,
    current_source_reverse_apply_check_pass=True,patch_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
    no_runtime_configuration_or_private_evidence_in_patch=True)
(root/'reference/kernel158/consolidated-patch-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
