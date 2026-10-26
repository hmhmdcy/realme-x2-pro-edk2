from pathlib import Path
import json, subprocess, re, struct, shutil, tarfile, hashlib
ref=Path(__file__).resolve().parent
out=Path('/mnt/e/edk2-samurai-out/kernel75/userspace')
root=out/'root'
bundle=out/'bundle'
bundle.mkdir(exist_ok=True)
glslang=out/'host/usr/bin/glslangValidator'
headers=[]
for stage,name in (('vert','vertex'),('frag','fragment')):
    target=out/('triangle.'+stage+'.spv')
    subprocess.run([str(glslang),'-V','--target-env','vulkan1.2',str(ref/('triangle.'+stage)),'-o',str(target)],check=True)
    data=target.read_bytes(); words=struct.unpack('<'+'I'*(len(data)//4),data)
    headers.append('static const uint32_t '+name+'_spv[] = {'+','.join(hex(x) for x in words)+'};\n')
(ref/'shaders.h').write_text(''.join(headers))
subprocess.run(['aarch64-linux-gnu-gcc','-O2','-Wall','-Wextra','-Werror','-I'+str(root/'usr/include'),str(ref/'gpu-render.c'),'-L'+str(root/'usr/lib/aarch64-linux-gnu'),'-Wl,-rpath-link,'+str(root/'usr/lib/aarch64-linux-gnu'),'-lvulkan','-o',str(bundle/'gpu-render')],check=True)
pending=[bundle/'gpu-render',root/'usr/lib/aarch64-linux-gnu/libvulkan_freedreno.so']
done=set()
lib=bundle/'lib';lib.mkdir(exist_ok=True)
while pending:
    path=pending.pop()
    if path.name in done: continue
    done.add(path.name)
    if path!=bundle/'gpu-render': shutil.copyfile(path,lib/path.name)
    dyn=subprocess.check_output(['readelf','-d',str(path)],text=True)
    for name in re.findall(r'\(NEEDED\).*?\[(.*?)\]',dyn):
        if name in done: continue
        candidates=list((root/'usr/lib/aarch64-linux-gnu').glob(name))+list((root/'lib/aarch64-linux-gnu').glob(name))+list((root/'usr/lib').glob(name))+list((root/'lib').glob(name))
        assert candidates,('missing library',name)
        pending.append(candidates[0])
(bundle/'freedreno.json').write_text(json.dumps({'file_format_version':'1.0.0','ICD':{'library_path':'/tmp/k75-gpu/lib/libvulkan_freedreno.so','api_version':'1.3.0'}},indent=2)+'\n')
packages=[]
for p in sorted((out/'debs').glob('*.deb')):
    fields=subprocess.check_output(['dpkg-deb','-f',str(p),'Package','Version','Architecture','Source'],text=True)
    packages.append({'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'package_metadata':fields})
manifest={'distribution':'Ubuntu 26.04 resolute main/universe arm64','source':'https://ports.ubuntu.com/ubuntu-ports','signed_apt_index_verified':True,'mesa':'26.0.3-1ubuntu1','bundled_files':{str(p.relative_to(bundle)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(bundle.rglob('*')) if p.is_file()},'downloaded_packages':packages}
(ref/'userspace-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
with tarfile.open(out.parent/'gpu-userspace.tar.gz','w:gz') as tar: tar.add(bundle,arcname='k75-gpu')
print('Cross-built actual-device Vulkan test; dependency closure '+str(len(done))+' ELF files; ICD restricted to Turnip.')
