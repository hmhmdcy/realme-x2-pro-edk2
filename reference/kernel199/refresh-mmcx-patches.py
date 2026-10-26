from pathlib import Path
import difflib,hashlib,json
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel199');p=k/'drivers/media/platform/qcom/camss/camss-cpas.c';s=p.read_text();rows=s.splitlines(True);i=next(i for i,l in enumerate(rows) if 'cpas->mmcx_link = device_link_add(' in l);column=rows[i].expandtabs(8).index('device_link_add(')+len('device_link_add(');indent='\t'*(column//8)+' '*(column%8)
for j in [i+1,i+2]:rows[j]=indent+rows[j].lstrip()
p.write_text(''.join(rows));oldpatch=ref/'camss-mmcx-runtime.patch';backup=out/'combined-mmcx-before-style-private.patch';assert not backup.exists();backup.write_bytes(oldpatch.read_bytes());r=json.loads((ref/'mmcx-source-validation.json').read_text());fields=list(r['source_sha256']);groups={'camss-mmcx-runtime.patch':fields[:3],'sm8150-camss-mmcx-domain.patch':[fields[3]],'sm8150-camss-mmcx-binding.patch':[fields[4]]}
for dest,names in groups.items():
 patch=''
 for n in names:
  before=(out/(Path(n).name+'.before199-private')).read_text();after=(k/n).read_text();patch+='diff --git a/'+n+' b/'+n+'\n'+''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+n,tofile='b/'+n))
 (ref/dest).write_text(patch)
r['source_sha256']={n:hashlib.sha256((k/n).read_bytes()).hexdigest() for n in fields};r['patch_series_separates_binding_dts_and_driver']=True;(ref/'mmcx-source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print('Driver alignment corrected; binding, DTS and driver split into three patches')
