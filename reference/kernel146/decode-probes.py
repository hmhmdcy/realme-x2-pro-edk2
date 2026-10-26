from pathlib import Path
import hashlib
import json
import os
import re
import runpy
import subprocess
import tarfile

ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel146')
out=Path('/mnt/e/edk2-samurai-out/kernel146')
runpy.run_path(str(ref.parent / 'kernel118/ensure-build-volume.py'))
mesa=Path('/home/cy122/pmos-samurai-kernel118/mesa-offline')
decoder=mesa / 'decode-build/src/freedreno/decode/crashdec'
reports={}
for label in ['baseline145','candidate146','noubwc146','sysmem146','nobin146','notile146','rd146','flush146']:
    with tarfile.open(out / (label+'-private.tar.gz')) as archive:
        data={m.name.removeprefix('./'):archive.extractfile(m).read() for m in archive if m.isfile()}
    for line in data['SHA256SUMS'].decode().splitlines():
        digest,name=line.split('  ',1)
        assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest()==digest
    summary=json.loads(data['result.json'])
    summary['archive_members_verified']=len(data)
    reports[label]=summary
    summary['decoded_gpu_cores']=[]
    summary['other_diagnostic_cores']=[]
    folder=out / (label+'-decoded-private')
    folder.mkdir(exist_ok=True)
    for name,content in data.items():
        if not name.endswith('-private.data'): continue
        core=folder / name
        core.write_bytes(content)
        if b'gpu-initialized:' not in content or b'revision:' not in content:
            summary['other_diagnostic_cores'].append(name)
            continue
        log=folder / (name+'.txt')
        if not log.exists():
            with log.open('wb') as stream:
                result=subprocess.run([str(decoder),'-s','-f',str(core)],stdout=stream,
                    stderr=subprocess.STDOUT,timeout=60,
                    env=dict(os.environ,RNN_PATH=str(mesa / 'mesa-26.2.4/src/freedreno/registers')))
            if result.returncode:
                raise RuntimeError(f'{label}/{name}: crashdec failed {result.returncode}; see private log')
        summary['decoded_gpu_cores'].append(name)
        text=log.read_text()
        lines=[x for x in text.splitlines() if re.search(r'RB_CCU_DBG_ECO_CNTL:|RB_NC_MODE_CNTL:|UCHE_MODE_CNTL:|RB_CCU_CNTL:|RB_DEPTH_PLANE_CNTL:',x)]
        print(label, '\n'.join(dict.fromkeys(lines)), flush=True)
(ref / 'probe-comparison-validation.json').write_text(json.dumps(reports,indent=2)+'\n')
print('K146_THREE_PROBE_ARCHIVES_MEMBERS_VERIFIED_CORES_DECODED')
