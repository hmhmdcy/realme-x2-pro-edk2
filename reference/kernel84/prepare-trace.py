"""Preserve the accepted source/initramfs; add bounded boot display tracing."""
from pathlib import Path
import hashlib,json,shutil,subprocess,os
K=Path('/home/cy122/x2pro-linux/linux')
R=Path('/home/cy122/edk2-samurai/repo')
I=Path('/home/cy122/x2pro-linux/initramfs')
O=Path('/mnt/e/edk2-samurai-out/kernel84')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip()=='7c53c0b4104900b2ffc3656a4415db8ef946d74b'
assert not subprocess.check_output(['git','-C',str(R),'status','--porcelain'])
assert sha(K/'.config')=='9d9f10ae4a96e4a0575b7c51d818180a68e596e84898a3849fe1183307223c6d'
assert sha(K/'arch/arm64/boot/Image')=='f90e6807bad34db3f3c88206ec952b0de78775272e407eb525ea2440ded476bb'
assert (O/'display-bootconfig.txt').is_file()
assert not (O/'preserved-private-manifest.json').exists()
tracked=subprocess.check_output(['git','-C',str(K),'ls-files','-m','-z']).decode().split('\0')
untracked=subprocess.check_output(['git','-C',str(K),'ls-files','--others','--exclude-standard','-z']).decode().split('\0')
names=sorted(set(n for n in tracked+untracked if n))
names+=['drivers/power/supply/bq27xxx_battery.c','drivers/power/supply/bq27xxx_battery_i2c.c','drivers/gpu/drm/msm/disp/dpu1/dpu_trace.h']
sources={n:sha(K/n) for n in names}
init={str(p.relative_to(I)):{'sha256':sha(p),'mode':p.stat().st_mode&0o777} for p in I.rglob('*') if p.is_file() and not p.is_symlink()}
links={str(p.relative_to(I)):os.readlink(p) for p in I.rglob('*') if p.is_symlink()}
for name,p in {'config-before':K/'.config','Image-before':K/'arch/arm64/boot/Image','cpio-before':K/'usr/initramfs_data.cpio',
               'boot-before.img':O.parent/'kernel79/boot-k79-bus.img','logdump-before.img':O.parent/'kernel75/logdump-k75-final.img'}.items():
    assert not (O/name).exists();shutil.copyfile(p,O/name)
assert sha(O/'boot-before.img')=='08edf9bcc1c55977169b0a8fd9f963805ba98d0423929e09e17bb9f811ca7405'
assert sha(O/'logdump-before.img')=='607fc6b4b0caba8ca5c7ea6677fd8259c81a216f91b2d6de7603e3f56d9881d0'
snapshot={'kernel_head':subprocess.check_output(['git','-C',str(K),'rev-parse','HEAD'],text=True).strip(),'sources':sources,'initramfs_files':init,'initramfs_links':links,
          'config_before_sha256':sha(O/'config-before'),'Image_before_sha256':sha(O/'Image-before'),'cpio_before_sha256':sha(O/'cpio-before'),
          'boot_before_sha256':sha(O/'boot-before.img'),'logdump_before_sha256':sha(O/'logdump-before.img'),'bootconfig_sha256':sha(O/'display-bootconfig.txt')}
(O/'preserved-private-manifest.json').write_text(json.dumps(snapshot,indent=2)+'\n')
# Only event tracing: no function instrumentation, dynamic debug or latency tracers.
subprocess.run([str(K/'scripts/config'),'--file',str(K/'.config'),'--enable','FTRACE','--enable','ENABLE_DEFAULT_TRACERS','--enable','BOOTTIME_TRACING',
                '--enable','BOOT_CONFIG_EMBED','--enable','BOOT_CONFIG_FORCE','--set-str','BOOT_CONFIG_EMBED_FILE',str(O/'display-bootconfig.txt'),
                '--enable','TRACER_SNAPSHOT','--disable','FUNCTION_TRACER','--disable','FUNCTION_GRAPH_TRACER','--disable','DYNAMIC_DEBUG'],check=True)
with (O/'olddefconfig.log').open('w') as log:
    subprocess.run(['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','olddefconfig'],cwd=K,stdout=log,stderr=subprocess.STDOUT,check=True)
def options(path):
    result={}
    for s in path.read_text().splitlines():
        if s.startswith('CONFIG_'):key,value=s.split('=',1);result[key]=value
        elif s.startswith('# CONFIG_') and s.endswith(' is not set'):result[s[2:-11]]='n'
    return result
before=options(O/'config-before');after=options(K/'.config')
diff={k:{'before':before.get(k),'after':after.get(k)} for k in sorted(before.keys()|after.keys()) if before.get(k)!=after.get(k)}
assert after['CONFIG_FTRACE']==after['CONFIG_TRACING']==after['CONFIG_EVENT_TRACING']=='y'
assert after['CONFIG_BOOTTIME_TRACING']==after['CONFIG_BOOT_CONFIG_EMBED']==after['CONFIG_TRACER_SNAPSHOT']=='y'
assert after['CONFIG_FUNCTION_TRACER']=='n' and after['CONFIG_DYNAMIC_DEBUG']=='n'
assert before['CONFIG_CMDLINE']==after['CONFIG_CMDLINE']=='""'
# No change in a hardware driver, source selection, initramfs, firmware or clock policy.
for k,v in before.items():
    if any(k.startswith('CONFIG_'+p) for p in ['DRM','BQ','POWER_SUPPLY','I2C','USB','PHY','ATH','WLAN','QCOM','REGULATOR','INITRAMFS','CMDLINE','LOCALVERSION','RMI','PM','SUSPEND','CPU_FREQ']):assert after[k]==v,k
for n,digest in sources.items():assert sha(K/n)==digest,n
(O/'config-delta.json').write_text(json.dumps(diff,indent=2)+'\n')
shutil.copyfile(K/'.config',O/'config-trace')
print('Prepared event-only display trace config;',len(diff),'tracing/config dependency changes; all tracked dirty sources and initramfs preserved.')
print(json.dumps(diff,indent=2))
