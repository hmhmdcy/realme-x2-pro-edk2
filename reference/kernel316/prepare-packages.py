"""Create a reproducible r25/r20 recipe from r24 plus the hardware handler."""
from pathlib import Path
import difflib,hashlib,json,shutil
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
BASE=SDK/'work/libcamera278-r24-r3-built/src/libcamera-v0.7.2'
INLINE=SDK/'work/libcamera299-inline';OLD=HERE.parent/'kernel313'
sources={}
for directory,target,origin in [('pipeline','src/libcamera/pipeline/camss-vfe',HERE),('ipa','src/ipa/camss-vfe',OLD)]:
 for p in (origin/directory).iterdir():
  if p.is_file():sources[target+'/'+p.name]=p
for p in (HERE/'framework').rglob('*'):
 if p.is_file():sources[p.relative_to(HERE/'framework').as_posix()]=p
sources['include/libcamera/ipa/camss.mojom']=OLD/'camss.mojom'
sources['include/linux/qcom-camss-config.h']=Path('/home/cy122/x2pro-linux/camera309-link-kernel/include/uapi/linux/qcom-camss-config.h')
sources['include/linux/media/v4l2-isp.h']=INLINE/'include/linux/media/v4l2-isp.h'
for rel in ['meson.build','meson_options.txt','include/libcamera/ipa/meson.build']:sources[rel]=INLINE/rel
for rel in ['src/ipa/camss-vfe/params.h','include/libcamera/internal/framebuffer.h','src/libcamera/v4l2_videodevice.cpp','include/linux/videodev2.h']:sources[rel]=INLINE/rel
patch=[];hashes={}
for rel,p in sources.items():
 before=(BASE/rel).read_text() if (BASE/rel).exists() else ''
 after=p.read_text();hashes[rel]=hashlib.sha256(after.encode()).hexdigest()
 patch.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+rel if before else '/dev/null',tofile='b/'+rel))
name='0029-camss-hardware-pipeline.patch';(HERE/name).write_text(''.join(patch))
recipes=HERE/'recipes';recipes.mkdir(exist_ok=True)
for package in ['libcamera','samurai-camera-config']:
 dest=recipes/package;assert not dest.exists();dest.mkdir()
 for p in (ROOT/'linux-port/packages'/package).iterdir():
  if p.is_file() and p.name not in ['README.md','source-lock.json']:shutil.copyfile(p,dest/p.name)
lib=recipes/'libcamera';shutil.copyfile(HERE/name,lib/name)
p=lib/'APKBUILD';s=p.read_text();assert 'pkgrel=24\n' in s
s=s.replace('pkgrel=24\n','pkgrel=25\n').replace('# Realme X2 Pro: retain the distro feature set; add IMX471 and first-frame fixes.','# Realme X2 Pro: full framework with CAMSS hardware processing and RAW support.')
needle='\t0028-simple-contrast-autofocus.patch\n';assert s.count(needle)==1
s=s.replace(needle,needle+'\t'+name+'\n')
s=s.replace('\t\t-Dpipelines=auto,virtual \\\n','\t\t-Dpipelines=auto,virtual \\\n\t\t-Dipas=camss-vfe,ipu3,mali-c55,rkisp1,rpi/pisp,rpi/vc4,simple,vimc \\\n')
end=s.rfind('"')
s=s[:end]+hashlib.sha512((HERE/name).read_bytes()).hexdigest()+'  '+name+'\n'+s[end:];p.write_text(s)
device=recipes/'samurai-camera-config';p=device/'APKBUILD';s=p.read_text()
s=s.replace('pkgrel=19\n','pkgrel=20\n').replace('99990.7.2-r24','99990.7.2-r25').replace('Realme X2 Pro libcamera CPU ISP and generic camera heap access','Realme X2 Pro CAMSS hardware tuning, software fallback and camera heap access')
models=['s5kgw1','imx471','imx319','s5k3m5']
for model in models:shutil.copyfile(OLD/(model+'.yaml'),device/('camss-'+model+'.yaml'))
needle='source="configuration.yaml samurai-camera-heaps.conf 70-samurai-camera-heaps.rules s5kgw1.yaml"'
assert needle in s;s=s.replace(needle,needle[:-1]+' '+' '.join('camss-'+m+'.yaml' for m in models)+'"')
needle='package() {\n';assert s.count(needle)==1
s=s.replace(needle,needle+'\tfor model in '+' '.join(models)+'; do\n\t\tinstall -Dm644 "$srcdir"/camss-$model.yaml "$pkgdir"/usr/share/libcamera/ipa/camss-vfe/$model.yaml\n\tdone\n')
end=s.rfind('"');s=s[:end]+''.join(hashlib.sha512((device/('camss-'+m+'.yaml')).read_bytes()).hexdigest()+'  camss-'+m+'.yaml\n' for m in models)+s[end:];p.write_text(s)
for package,dest in [('libcamera',SDK/'work/libcamera316-r25'),('samurai-camera-config',SDK/'work/samurai-camera-config316-r25')]:
 assert not dest.exists();shutil.copytree(recipes/package,dest)
(HERE/'package-source-validation.json').write_text(json.dumps(dict(stage=316,framework_version='99990.7.2-r25',configuration_version='0.1.0-r20',incremental_patch=name,changed_source_sha256=hashes,prior28_patches_preserved=True,profiles_stage=313,system_installed=False),indent=2)+'\n')
print('Prepared r25 framework / r20 config recipes and cumulative hardware patch.')
