from pathlib import Path
import runpy,subprocess,tempfile,json
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel118/ensure-build-volume.py')
root=Path('/home/cy122/pmos-samurai-kernel118');old=root/'kernel';new=root/'camera120/kernel'
modules=lambda tree:{str(p.relative_to(tree)):p for p in tree.rglob('*.ko')}
a=modules(old);b=modules(new);changed=[]
with tempfile.TemporaryDirectory(prefix='module-check-',dir=root/'camera120') as temp:
    temp=Path(temp)
    for name in sorted(a.keys()&b.keys()):
        for src,dest in [(a[name],temp/'old.ko'),(b[name],temp/'new.ko')]:
            subprocess.run(['aarch64-linux-gnu-strip','--strip-debug','--remove-section=.note.gnu.build-id','-o',str(dest),str(src)],check=True)
        if (temp/'old.ko').read_bytes()!=(temp/'new.ko').read_bytes():changed.append(name)
report=dict(baseline118_modules=len(a),candidate120_modules=len(b),common_modules=len(a.keys()&b.keys()),changed_common_modules=changed,new_modules=sorted(b.keys()-a.keys()),removed_modules=sorted(a.keys()-b.keys()),full_rootfs120_not_generated=True,not_deployed=True)
Path('/mnt/e/RealmeX2Pro edk2/reference/kernel120/module-comparison-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
