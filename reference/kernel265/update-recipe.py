"""Update the pinned complete recipe to the exact deployed r3 source inputs."""
from pathlib import Path
import difflib,hashlib,json,re,shutil
import host
R=Path(__file__).parent;repo=R.parents[1];out=repo/'linux-port/packages/pipewire-common';SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');W=SDK/'work/pipewire265-retained-busy'
backup=host.PRIVATE/'recipe-r2-before-private';assert not backup.exists();shutil.copytree(out,backup)
patches={
 '0004-libcamera-buffer-lifecycle.patch':(R/'libcamera-fresh-allocation-candidate.patch').read_bytes(),
 '0005-memory-region-lookup.patch':(R/'core-map-lookup-candidate.patch').read_bytes()
}
base=SDK/'work/pipewire262/pipewire-profile/src/gst';patch=''
for name in ['gstpipewirepool.h','gstpipewirepool.c','gstpipewiresrc.c']:
 patch+=''.join(difflib.unified_diff((base/name).read_text().splitlines(True),(W/'v4/source'/name).read_text().splitlines(True),fromfile='a/src/gst/'+name,tofile='b/src/gst/'+name))
(R/'gst-retained-busy-v4-candidate.patch').write_text(patch);patches['0006-gst-retained-buffer-ownership.patch']=patch.encode()
for name,data in patches.items():(out/name).write_bytes(data)
p=out/'APKBUILD';s=p.read_text();assert 'pkgrel=2' in s;s=s.replace('pkgrel=2','pkgrel=3',1)
needle='\t0004-libcamera-buffer-lifecycle.patch\n';assert s.count(needle)==1
s=s.replace(needle,needle+'\t0005-memory-region-lookup.patch\n\t0006-gst-retained-buffer-ownership.patch\n')
needle='depends="pipewire-session-manager gst-plugins-base"';assert s.count(needle)==1
s=s.replace(needle,'depends="pipewire-session-manager gst-plugins-base pipewire-libs=$pkgver-r$pkgrel"')
for name in patches:
 digest=hashlib.sha512((out/name).read_bytes()).hexdigest()
 pattern=r'^[0-9a-f]{128}  '+re.escape(name)+r'$'
 if re.search(pattern,s,re.M):s=re.sub(pattern,digest+'  '+name,s,flags=re.M)
 else:
  end=s.rfind('"');s=s[:end]+digest+'  '+name+'\n'+s[end:]
p.write_text(s)
lock=json.loads((out/'source-lock.json').read_text());lock.update(stage=265,version='1.6.9-r3',paired_dependency='pipewire-spa-libcamera and gst-plugin-pipewire depend on pipewire-libs=1.6.9-r3')
queue=['0001-gst-defer-pool-recycle.patch','0002-gst-optional-camera-copy.patch','0003-camera-broadcast-lifecycle.patch','0004-libcamera-buffer-lifecycle.patch','0005-memory-region-lookup.patch','0006-gst-retained-buffer-ownership.patch']
lock['patch_sha256']={n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in queue}
(out/'source-lock.json').write_text(json.dumps(lock,indent=2)+'\n')
original=Path('/home/cy122/x2pro-linux/pipewire264-recipe-qa/APKBUILD');assert hashlib.sha256(original.read_bytes()).hexdigest()=='09f9941b7f06c4c22fa8258b9beed39be39181250dddec882d3d75ac2cfcbac9'
(R/'upstream-recipe-overlay.patch').write_text(''.join(difflib.unified_diff(original.read_text().splitlines(True),s.splitlines(True),fromfile='a/community/pipewire/APKBUILD',tofile='b/community/pipewire/APKBUILD')))
print(json.dumps(dict(updated=True,version='1.6.9-r3',project_patches=len(queue))))

