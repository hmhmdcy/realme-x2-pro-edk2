"""Inspect retained primary TMC sources and target code, without phone access."""
from pathlib import Path
import hashlib,importlib.util,json,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354'
state=json.loads((HERE.parent/'kernel410/source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
state.update(stage=411,source_unchanged_from410=True,tmc_target_knee_pending=True,
    phone_accessed=False,new_hardware_verification=False,last_device_evidence_stage=406)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
repo='/home/cy122/x2pro-linux/refs/CamxChi-k117';rev='9f17f1b568626b393e785b369c5dc94543774d7a'
paths=['camx/src/hwl/iqinterpolation/tmc10interpolation.cpp',
       'camx/src/hwl/iqinterpolation/tmc11interpolation.cpp',
       'camx/src/hwl/ispiqmodule/camxiqinterface.cpp',
       'camx/src/hwl/ispiqmodule/camxswtmc10.cpp','camx/src/hwl/ispiqmodule/camxswtmc11.cpp']
files=subprocess.check_output(['git','-C',repo,'ls-tree','-r','--name-only',rev],text=True).splitlines()
print('TMC source paths',*[f for f in files if 'tmc' in f.lower() and f.endswith(('.cpp','.h'))],sep='\n')
out=P/'sources';out.mkdir(exist_ok=True);rows=[]
for path in paths:
    if path not in files:continue
    raw=subprocess.check_output(['git','-C',repo,'show',rev+':'+path],timeout=45)
    (out/Path(path).name).write_bytes(raw)
    rows.append(dict(path=path,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),url='https://github.com/bjzhou/CamxChi/blob/'+rev+'/'+path))
(HERE/'primary-sources.json').write_text(json.dumps(dict(stage=411,commit=rev,files=rows),indent=2)+'\n')
raw=(P.parent/'kernel281/camera.qcom.so-private').read_bytes()
print('target string markers')
for needle in [b'TMC10',b'TMC11',b'CalcGainCurve',b'CalculateKneePoints',b'SWTMC']:
    pos=0
    while True:
        pos=raw.find(needle,pos)
        if pos<0:break
        start=raw.rfind(b'\0',max(0,pos-100),pos)+1;end=raw.find(b'\0',pos)
        print(hex(pos),raw[start:end].decode(errors='replace')[:200]);pos+=len(needle)
q=subprocess.run(['aarch64-linux-gnu-objdump','-d','--start-address=0x3c3000','--stop-address=0x3c6330',str(P.parent/'kernel281/camera.qcom.so-private')],capture_output=True,check=True)
(P/'before-sampler-private.asm').write_bytes(q.stdout)
print('source and target inspection retained')
