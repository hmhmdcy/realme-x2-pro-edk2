"""Apply the verified typed conversion chain without changing DMA teardown."""
from pathlib import Path
import importlib.util,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
for name in ['parcel-validation.json','transfer-validation.json','firmware-parcel-validation.json']:assert json.loads((HERE/name).read_text())['passed']
assert json.loads((HERE/'firmware-parcel-validation.json').read_text())['native_and_hal_whole_cdm_and_job_match_with_conversions']
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage);source=storage.mounted_build().parent/'source354'
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip();parent='8b1e8903a550ffc20a2d8f1de574c37f2260fff3'
assert git('rev-parse','HEAD')==parent and not git('status','--porcelain')
def fun(text,name):
 m=re.search(r'(?:static )?(?:bool|void|int)\s+'+name+r'\([^;]+?\n\{.*?^\}\n',text,re.S|re.M);assert m,name;return m[0]
old=(P/'camss-icp-a5-boot.c.before').read_text();new=(P/'camss-icp-a5-boot.c.proposed').read_text()
for n in ['free_memory','free_transfer_memory','free_imported_images','transfer_region_locked','quiesce_locked','stop_locked']:assert fun(old,n)==fun(new,n)
for n in ['camss_a5_ipe_job','camss_a5_ipe_frame']:
 before=(P/'camss-icp-a5-ipe.h.before').read_text();after=(P/'camss-icp-a5-ipe.h.proposed').read_text();assert re.search(r'struct '+n+r' \{.*?\n\};',before,re.S)[0]==re.search(r'struct '+n+r' \{.*?\n\};',after,re.S)[0]
names=json.loads((HERE/'proposal-validation.json').read_text())['files'];prefix='drivers/media/platform/qcom/camss/';paths=[prefix+n for n in names]
subprocess.run(['git','-C',str(source),'checkout','-b','samurai-ipe-conversions399'],check=True,capture_output=True)
for n in names:
 p=source/prefix/n;assert p.read_bytes()==(P/(n+'.before')).read_bytes();p.write_bytes((P/(n+'.proposed')).read_bytes())
subprocess.run(['git','-C',str(source),'diff','--check','--',*paths],check=True);subprocess.run(['git','-C',str(source),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(source),'commit','--only','-m','media: camss: own typed pre and post IPE conversion programs','--',*paths],check=True,capture_output=True)
assert not git('status','--porcelain')
d=dict(stage=399,parent=parent,source=str(source),branch=git('branch','--show-current'),commit=git('rev-parse','HEAD'),changed=paths,clean=True,installed=False,new_api='camss_a5_ipe_run_colour_chain_status',old_apis_job_and_frame_layout_retained=True,reset_unknown_completion_and_dma_teardown_functions_unchanged=True,existing4096_iq_page_reused=True)
(HERE/'source-state.json').write_text(json.dumps(d,indent=2)+'\n');(HERE/'build-intree.py').write_text((HERE.parent/'kernel398/build-intree.py').read_text().replace('stage=398','stage=399'))
print(json.dumps(d,indent=2))
