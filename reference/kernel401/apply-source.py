"""Apply typed Gamma ownership while preserving reset and DMA teardown."""
from pathlib import Path
import importlib.util,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
for n in ['contract-validation.json','parcel-validation.json','transfer-validation.json','firmware-parcel-validation.json']:assert json.loads((HERE/n).read_text())['passed']
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage);source=storage.mounted_build().parent/'source354'
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip();parent='de94e65e7ab4ae2ec23ee1665f981d0aeb7395e7';assert git('rev-parse','HEAD')==parent and not git('status','--porcelain')
def fun(text,name):
 m=re.search(r'(?:static )?(?:bool|void|int)\s+'+name+r'\([^;]+?\n\{.*?^\}\n',text,re.S|re.M);assert m,name;return m[0]
old=(P/'camss-icp-a5-boot.c.before').read_text();new=(P/'camss-icp-a5-boot.c.proposed').read_text()
for n in ['free_memory','free_transfer_memory','free_imported_images','transfer_region_locked','quiesce_locked','stop_locked']:assert fun(old,n)==fun(new,n)
for n in ['camss_a5_ipe_job','camss_a5_ipe_frame']:
 oldh=(P/'camss-icp-a5-ipe.h.before').read_text();newh=(P/'camss-icp-a5-ipe.h.proposed').read_text();assert re.search(r'struct '+n+r' \{.*?\n\};',oldh,re.S)[0]==re.search(r'struct '+n+r' \{.*?\n\};',newh,re.S)[0]
names=json.loads((HERE/'proposal-validation.json').read_text())['files'];prefix='drivers/media/platform/qcom/camss/';paths=[prefix+n for n in names]
subprocess.run(['git','-C',str(source),'checkout','-b','samurai-ipe-gamma401'],check=True,capture_output=True)
for n in names:
 p=source/prefix/n;assert p.read_bytes()==(P/(n+'.before')).read_bytes();p.write_bytes((P/(n+'.proposed')).read_bytes())
subprocess.run(['git','-C',str(source),'diff','--check','--',*paths],check=True);subprocess.run(['git','-C',str(source),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(source),'commit','--only','-m','media: camss: own typed Gamma LUTs in the retained IPE request','--',*paths],check=True,capture_output=True)
assert not git('status','--porcelain')
d=dict(stage=401,parent=parent,source=str(source),branch=git('branch','--show-current'),commit=git('rev-parse','HEAD'),changed=paths,clean=True,installed=False,new_api='camss_a5_ipe_run_gamma_status',generic_program_type=20,gamma_program_type=12,gamma_lut_owned_in_request=True,new_independent_coherent_allocations=0,temporary_cpu_copy_bytes=3072,iq_bytes=6016,iq_page_allocation_bytes=8192,old_layouts_reset_and_dma_teardown_unchanged=True)
(HERE/'source-state.json').write_text(json.dumps(d,indent=2)+'\n');(HERE/'build-intree.py').write_text((HERE.parent/'kernel399/build-intree.py').read_text().replace('stage=399','stage=401'));print(json.dumps(d,indent=2))
