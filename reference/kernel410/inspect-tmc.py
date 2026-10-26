"""Read bounded pinned sampling sources and retained target function."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354'
state=json.loads((HERE.parent/'kernel409/source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
state.update(stage=410,source_unchanged_from409=True,tmc_sampling_pending=True,
             phone_accessed=False,new_hardware_verification=False,last_device_evidence_stage=406)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
repo='/home/cy122/x2pro-linux/refs/CamxChi-k117';rev='9f17f1b568626b393e785b369c5dc94543774d7a'
out=P/'sources';out.mkdir(exist_ok=True);rows=[]
paths=['camx/src/hwl/iqsetting/iqsettingutil.cpp','camx/src/hwl/iqinterpolation/tmc10interpolation.cpp',
       'camx/src/hwl/iqinterpolation/tmc10interpolation.h','chi-cdk/api/chromatix/XSD/isp/tmc_1_0_0.xsd',
       'camx/src/hwl/iqinterpolation/iqcommondefs.h','camx/src/hwl/iqsetting/iqsettingutil.h']
for path in paths:
    name=Path(path).name;raw=subprocess.check_output(['git','-C',repo,'show',rev+':'+path],timeout=45)
    (out/name).write_bytes(raw);rows.append(dict(path=path,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),url='https://github.com/bjzhou/CamxChi/blob/'+rev+'/'+path))
    text=raw.decode();print(name,len(raw))
    if name=='iqsettingutil.cpp':
        i=text.index('BOOL IQSettingUtils::GainCurveSampling(');brace=text.index('{',i);end=brace+1;depth=1
        while depth:depth+=(text[end]=='{')-(text[end]=='}');end+=1
        print(text[i:end])
(HERE/'primary-sources.json').write_text(json.dumps(dict(stage=410,commit=rev,files=rows),indent=2)+'\n')
hal=P.parent/'kernel281/camera.qcom.so-private'
q=subprocess.run(['aarch64-linux-gnu-objdump','-d','--start-address=0x3c6328','--stop-address=0x3c7070',str(hal)],capture_output=True,check=True)
(P/'gain-sampling-private.asm').write_bytes(q.stdout)
