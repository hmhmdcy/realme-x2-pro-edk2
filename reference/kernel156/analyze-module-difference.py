from pathlib import Path
import hashlib,json,re,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel156')
k=Path('/home/cy122/pmos-samurai-kernel136')
modules=k/'modules-root156'
with tarfile.open(out.parent/'kernel132/modules-k132-private.tar.gz') as tar:
    old={m.name:tar.extractfile(m).read() for m in tar if m.isfile() and m.name.endswith('.ko')}
new={str(p.relative_to(modules)):p.read_bytes() for p in modules.rglob('*.ko')}
assert len(new)==len(old)==770 and new.keys()==old.keys()
rows=[];unexplained=[]
for name,before in old.items():
    after=new[name]
    if before==after:continue
    a=re.findall(rb'srcversion=[0-9A-F]{24}\x00',before)
    b=re.findall(rb'srcversion=[0-9A-F]{24}\x00',after)
    metadata_only=len(a)==len(b)==1 and after.replace(b[0],a[0],1)==before
    rows.append(dict(module=name,srcversion_only=metadata_only,
        before_sha256=hashlib.sha256(before).hexdigest(),after_sha256=hashlib.sha256(after).hexdigest()))
    if not metadata_only:unexplained.append(name)
report=dict(stage=156,total_modules=770,changed_modules=len(rows),
    unchanged_modules=770-len(rows),all_differences_only_srcversion=not unexplained,
    unexplained_modules=unexplained,rows=rows,module_deployment_decision_pending=True)
(out/'module-difference-private.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='rows'}),flush=True)
assert not unexplained,unexplained
