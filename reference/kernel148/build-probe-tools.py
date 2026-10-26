from pathlib import Path
import os, subprocess
sdk = Path('/tmp/k148-sdk')
gccdir = next((sdk/'usr/lib/gcc').glob('aarch64-*/*'))
out = Path('/var/lib/samurai/k148-tools'); out.mkdir(mode=0o755,exist_ok=True)
env = dict(os.environ,PATH=str(sdk/'usr/bin')+':'+os.environ['PATH'],
           LD_LIBRARY_PATH=str(sdk/'usr/lib')+':'+str(sdk/'lib'))
common = [str(sdk/'usr/bin/gcc'),'--sysroot='+str(sdk),'-B'+str(gccdir)+'/',
          '-B'+str(sdk/'usr/bin')+'/', '-O2','-Wall','-Wextra']
with (out/'compiler-private.log').open('wb') as f:
    subprocess.run(common+['-shared','-fPIC','/tmp/k148-vm-bind-tap.c','-ldl',
                          '-o',str(out/'vm-bind-tap.so')],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
os.chmod(out/'vm-bind-tap.so',0o755)
if Path('/tmp/k148-vulkan-pixel-probe.c').exists():
    with (out/'pixel-compiler-private.log').open('wb') as f:
        subprocess.run(common+['/tmp/k148-vulkan-pixel-probe.c','-L/usr/lib','-l:libvulkan.so.1','-o',str(out/'vulkan-pixel-probe')],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
        for stage in ['vert','frag']:
            subprocess.run([str(sdk/'usr/bin/glslangValidator'),'-V','/tmp/k148-probe.'+stage,'-o',str(out/('probe.'+stage+'.spv'))],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
if Path('/tmp/k148-vulkan-memory-probe.c').exists():
    with (out/'memory-compiler-private.log').open('wb') as f:
        subprocess.run(common+['/tmp/k148-vulkan-memory-probe.c','-L/usr/lib','-l:libvulkan.so.1','-o',str(out/'vulkan-memory-probe')],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
print('K148_IOCTL_TAP_COMPILED')
