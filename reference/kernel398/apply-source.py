"""Apply only the validated offset correction to the retained candidate."""
from pathlib import Path
import importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
for n in ['caller-validation.json','colour-validation.json','parcel-validation.json']:assert json.loads((HERE/n).read_text())['passed']
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
parent='6a6451dd1fa14534e5c805d8ca8e9a588b42016d';assert git('rev-parse','HEAD')==parent and not git('status','--porcelain')
names=['camss-icp-a5-colour.c','camss-icp-a5-colour.h'];prefix='drivers/media/platform/qcom/camss/'
subprocess.run(['git','-C',str(source),'checkout','-b','samurai-ipe-offset398'],check=True,capture_output=True)
for n in names:
 p=source/prefix/n;assert p.read_bytes()==(P/(n+'.before')).read_bytes();p.write_bytes((P/(n+'.proposed')).read_bytes())
paths=[prefix+n for n in names]
subprocess.run(['git','-C',str(source),'diff','--check','--',*paths],check=True)
subprocess.run(['git','-C',str(source),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(source),'commit','--only','-m','media: camss: use actual IPE CC offset field width','--',*paths],check=True,capture_output=True)
assert not git('status','--porcelain')
d=dict(stage=398,parent=parent,source=str(source),branch=git('branch','--show-current'),commit=git('rev-parse','HEAD'),changed=paths,clean=True,installed=False,only_offset_validation_and_masks_changed=True,job_frame_layout_and_dma_lifetime_functions_unchanged=True)
(HERE/'source-state.json').write_text(json.dumps(d,indent=2)+'\n')
(HERE/'build-intree.py').write_text((HERE.parent/'kernel397/build-intree.py').read_text().replace('stage=397','stage=398'))
print(json.dumps(d,indent=2))
