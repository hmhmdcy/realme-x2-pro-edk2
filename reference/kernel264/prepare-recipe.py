"""Publish a complete pinned Alpine recipe with the tested common patch queue."""
from pathlib import Path
import concurrent.futures,difflib,hashlib,json,re,urllib.request
R=Path(__file__).parent;repo=R.parents[1];P=Path('/mnt/e/edk2-samurai-out/kernel264');out=repo/'linux-port/packages/pipewire-common';assert not out.exists();out.mkdir()
commit='0afac626498565714f7a06c04589112584cc95f4'
names=['APKBUILD','pipewire.desktop','pipewire-launcher.sh','pipewire.initd','pipewire-pulse.initd','systemd-units-wo-libsystemd.patch','pipewire.post-upgrade','pipewire.post-install']
def fetch(name):
 url='https://raw.githubusercontent.com/alpinelinux/aports/'+commit+'/community/pipewire/'+name
 data=urllib.request.urlopen(url,timeout=20).read();return name,url,data
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:items=list(pool.map(fetch,names))
raw={name:data for name,url,data in items};assert hashlib.sha256(raw['APKBUILD']).hexdigest()=='09f9941b7f06c4c22fa8258b9beed39be39181250dddec882d3d75ac2cfcbac9'
sources={}
for name,url,data in items:
 original=data
 # Materialize upstream install-script symlinks, retaining their original blob hash.
 if data.decode().strip() in raw and not data.startswith(b'#!'):data=raw[data.decode().strip()]
 (out/name).write_bytes(data);sources[name]=dict(url=url,upstream_blob_sha256=hashlib.sha256(original).hexdigest(),materialized_sha256=hashlib.sha256(data).hexdigest())
patches=[('0001-gst-defer-pool-recycle.patch',repo/'linux-port/packages/gst-plugin-pipewire/0001-defer-pool-buffer-recycle.patch'),('0002-gst-optional-camera-copy.patch',repo/'linux-port/packages/gst-plugin-pipewire/0002-camera-copy-profile.patch'),('0003-camera-broadcast-lifecycle.patch',R/'core-binding-reset-candidate.patch'),('0004-libcamera-buffer-lifecycle.patch',R/'libcamera-reset-output-io-candidate.patch')]
for name,p in patches:(out/name).write_bytes(p.read_bytes())
original=raw['APKBUILD'].decode();s=original.replace('pkgrel=0','pkgrel=2',1)
old_url='https://gitlab.freedesktop.org/PipeWire/pipewire/-/archive/$pkgver/pipewire-$pkgver.tar.gz'
s=s.replace(old_url,'pipewire-$pkgver.tar.gz::https://github.com/PipeWire/pipewire/archive/refs/tags/$pkgver.tar.gz')
needle='\tsystemd-units-wo-libsystemd.patch\n\t"';assert s.count(needle)==1;s=s.replace(needle,'\tsystemd-units-wo-libsystemd.patch\n'+''.join('\t'+name+'\n' for name,p in patches)+'\t"')
start=s.index('libcamera() {');end=s.index('\n}',start);block=s[start:end];assert 'depends=""' in block
s=s[:start]+block.replace('depends=""','depends="pipewire-libs=$pkgver-r$pkgrel"')+s[end:]
tar_sha='91a4790123f95c2a52592e4dcd7de90add681883710d3baa068f973c1477c4a9b7696df6afedbcb6c9f42abfdfa10dc01c383aa5d7ced33d781287a07bb18fd3'
s,n=re.subn(r'^[0-9a-f]{128}  pipewire-\$?[^\s]*\.tar\.gz$',lambda m:tar_sha+'  '+m[0].split('  ',1)[1],s,count=1,flags=re.M);assert n==1
end=s.rfind('"');s=s[:end]+''.join(hashlib.sha512((out/name).read_bytes()).hexdigest()+'  '+name+'\n' for name,p in patches)+s[end:]
(out/'APKBUILD').write_text(s)
(R/'upstream-recipe-overlay.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile='a/community/pipewire/APKBUILD',tofile='b/community/pipewire/APKBUILD')))
lock=dict(stage=264,version='1.6.9-r2',alpine_commit=commit,upstream_recipe_files=sources,source_tar=dict(url='https://github.com/PipeWire/pipewire/archive/refs/tags/1.6.9.tar.gz',sha256='dbc3624cf71215c26a22fc98f6f71f7b8599f5f6b415eab4a5c90ca96c170c7c',sha512=tar_sha),patch_sha256={name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name,p in patches},paired_dependency='pipewire-spa-libcamera depends on pipewire-libs=1.6.9-r2',phone_packages_built_by_incremental_source_compile_and_signed_upstream_payload_repack=True,complete_abuild_recipe_prepared_not_full_build_yet=True)
(out/'source-lock.json').write_text(json.dumps(lock,indent=2)+'\n');print(json.dumps(dict(prepared=True,files=len(list(out.iterdir())),patches=len(patches),upstream_recipe_verified=True)))
