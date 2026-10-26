"""Inspect converter and blend ranges from retained target and pinned sources."""
from pathlib import Path
import hashlib,importlib.util,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354'
state=json.loads((HERE.parent/'kernel408/source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
state.update(stage=409,source_unchanged_from408=True,new_adrc_conversion_pending=True,
             phone_accessed=False,new_hardware_verification=False,last_device_evidence_stage=406)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
hal=P.parent/'kernel281/camera.qcom.so-private'
for name,start,end in [('adrc-converter-private.asm',0x362774,0x3642d4),
                       ('adrc-blend-private.asm',0x3642d4,0x364598)]:
    q=subprocess.run(['aarch64-linux-gnu-objdump','-d','--start-address='+hex(start),'--stop-address='+hex(end),str(hal)],capture_output=True,check=True)
    (P/name).write_bytes(q.stdout)
rows=[]
for path,relative in [(P.parent/'kernel403/sources/ltm13setting.cpp','camx/src/hwl/iqsetting/ltm13setting.cpp'),
                      (P.parent/'kernel333/sources/iqsettingutil.h','camx/src/hwl/iqsetting/iqsettingutil.h')]:
    raw=path.read_bytes();rows.append(dict(path=relative,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
        url='https://github.com/bjzhou/CamxChi/blob/9f17f1b568626b393e785b369c5dc94543774d7a/'+relative))
(HERE/'primary-sources.json').write_text(json.dumps(dict(stage=409,commit='9f17f1b568626b393e785b369c5dc94543774d7a',files=rows),indent=2)+'\n')
table=(P.parent/'kernel403/sources/camxipeltm13.cpp').read_text()
text=re.search(r'static UINT32 gamma64Table\[\] =\s*\{([^}]+)',table)[1]
print('reference fallback gamma nodes',len(re.findall(r'\d+',text)))
values=[];kinds=set()
for name in ['qtech_s5kgw1','sunny_s5kgw1','sunny_imx471','qtech_s5k3m5sx','sunny_imx319']:
    data=json.loads((P.parent/'kernel351'/(name+'-ltm13_ipe-trees-private.json')).read_text())
    for root in data:
        v=root['reserve']['ltm_curve_tab'];assert len(v)==65;values.extend(v);kinds.update(type(x).__name__ for x in v)
print(json.dumps(dict(reserve_curve_min=min(values),reserve_curve_max=max(values),value_types=sorted(kinds),
                     source_clean=True,phone_accessed=False)))
