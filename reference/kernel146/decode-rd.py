from pathlib import Path
import os, runpy, subprocess
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel146')
out=Path('/mnt/e/edk2-samurai-out/kernel146')
runpy.run_path(str(ref.parent / 'kernel118/ensure-build-volume.py'))
mesa=Path('/home/cy122/pmos-samurai-kernel118/mesa-offline')
env=dict(os.environ,RNN_PATH=str(mesa / 'mesa-26.2.4/src/freedreno/registers'))
rd=out / 'rd146-decoded-private/rd-glmark2-es2-wayland-fixed_combined.rd.gz'
import tarfile
with tarfile.open(out / 'rd146-private.tar.gz') as t:
    member=next(m for m in t if m.name.endswith(rd.name))
    rd.write_bytes(t.extractfile(member).read())
with (out / 'rd146-full-command-private.txt').open('wb') as f:
    subprocess.run([str(mesa / 'decode-build/src/freedreno/decode/cffdump'),'--once',str(rd)],env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=180)
source=mesa / 'mesa-26.2.4/src/gallium/drivers/freedreno/a6xx/fd6_gmem.cc'
s=source.read_text().splitlines()
with (out / 'gmem-fini-private.txt').open('w') as f:
    for i,line in enumerate(s):
        if any(k in line for k in ['fd6_emit_tile_fini(', 'emit_common_fini(', 'FD6_FLUSH_CCU', 'FD6_INVALIDATE_CCU']):
            f.write('\n'.join(f'{j+1}: {s[j]}' for j in range(max(0,i-15),min(len(s),i+65)))+'\n')
print('K146_RD_COMMANDS_DECODED')
