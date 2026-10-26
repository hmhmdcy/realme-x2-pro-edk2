from pathlib import Path
import concurrent.futures,hashlib,json,os,re,shutil,subprocess,tarfile,urllib.request
os.umask(0o077);here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel213');source_root=private/'source';source_root.mkdir(mode=0o700)
archive=private.parent/'kernel211/libcamera-v0.7.2.tar.gz'
expected='b317cdc96f61682ee0bf26dfb7c4d6441db9a9c5b93ab53528121a8cd44862b3d59cbaa3881bb0837e3e381564c184c7b742124aef4267eea754c6083de353c1'
assert hashlib.sha512(archive.read_bytes()).hexdigest()==expected
with tarfile.open(archive) as t:t.extractall(source_root,filter='data')
source=next(source_root.iterdir());port=Path('/home/cy122/pmos-samurai-rootfs01/pmaports/temp/libcamera');recipe=(port/'APKBUILD').read_text()
patches=private/'distro-patches';patches.mkdir(mode=0o700)
distro=[]
for path in sorted(port.glob('*.patch')):
    match=re.search(r'(?m)^([0-9a-f]{128})  '+re.escape(path.name)+r'$',recipe);assert match and hashlib.sha512(path.read_bytes()).hexdigest()==match[1]
    copy=patches/path.name;shutil.copyfile(path,copy)
    p=subprocess.run(['patch','-p1','--batch','--forward','--input',str(copy)],cwd=source,capture_output=True);(private/(path.name+'.apply-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0
    distro.append(dict(name=path.name,sha512=match[1]))
assert len(distro)==6
commits=['59e7f18952de3aaa5e4948928e7602779a02296d','e64b507de18774352cbe0bdfd51b637b00a56873']
def fetch(commit):
    errors=[]
    for url in ['https://git.libcamera.org/libcamera/libcamera.git/patch/?id='+commit,'https://gitlab.freedesktop.org/camera/libcamera/-/commit/'+commit+'.patch']:
        try:
            with urllib.request.urlopen(url,timeout=20) as response:data=response.read(2*1024*1024)
            assert data.startswith(('From '+commit+' ').encode()) and b'diff --git ' in data
            path=private/(commit+'.patch');path.write_bytes(data)
            return dict(commit=commit,url=url,sha256=hashlib.sha256(data).hexdigest(),subject=next(line for line in data.decode().splitlines() if line.startswith('Subject:')),files=re.findall(r'(?m)^diff --git a/(.*?) b/',data.decode()))
        except Exception as error:errors.append(type(error).__name__+': '+str(error))
    return dict(commit=commit,errors=errors)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:upstream=list(pool.map(fetch,commits))
report=dict(stage=213,pinned_libcamera_version='0.7.2',archive_sha512_verified=True,six_original_distro_patches_applied=True,distro_patches=distro,upstream=upstream,no_phone_product_change=True)
(here/'source-input-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(private/'source-location-private.json').write_text(json.dumps(dict(source=str(source),archive=str(archive)),indent=2)+'\n')
for name in ['meson_options.txt','meson.build','src/libcamera/software_isp/meson.build','include/libcamera/ipa/soft.mojom','include/libcamera/internal/software_isp/debayer_params.h']:
    path=source/name
    if path.is_file():print(json.dumps(dict(file=name,text=path.read_text())))
print(json.dumps(report))
