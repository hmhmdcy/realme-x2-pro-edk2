from pathlib import Path
import importlib.util,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
for n in ['transfer-validation.json','parcel-validation.json','firmware-parcel-validation.json']:assert json.loads((HERE/n).read_text())['passed']
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip();parent='46fdb7c96b04825dc1802f8280685a4c4e709615';assert git('rev-parse','HEAD')==parent and not git('status','--porcelain')
names=json.loads((HERE/'proposal-validation.json').read_text())['files'];base='drivers/media/platform/qcom/camss/'
def fun(text,name):
 m=re.search(r'(?:static )?(?:bool|void|int)\s+'+name+r'\([^;]+?\n\{.*?^\}\n',text,re.S|re.M);assert m,name;return m[0]
old=(P/'camss-icp-a5-boot.c.before').read_text();new=(P/'camss-icp-a5-boot.c.proposed').read_text()
for n in ['free_memory','free_transfer_memory','free_imported_images','transfer_region_locked','quiesce_locked','stop_locked']:assert fun(old,n)==fun(new,n)
oldjob=(P/'camss-icp-a5-ipe.h.before').read_text();newjob=(P/'camss-icp-a5-ipe.h.proposed').read_text()
for n in ['camss_a5_ipe_job','camss_a5_ipe_frame']:assert re.search(r'struct '+n+r' \{.*?\n\};',oldjob,re.S)[0]==re.search(r'struct '+n+r' \{.*?\n\};',newjob,re.S)[0]
subprocess.run(['git','-C',str(source),'checkout','-b','samurai-ipe-frame-colour397'],check=True,capture_output=True)
for n in names:
 target=source/base/n;assert target.read_bytes()==(P/(n+'.before')).read_bytes();target.write_bytes((P/(n+'.proposed')).read_bytes())
paths=[base+n for n in names];subprocess.run(['git','-C',str(source),'diff','--check','--',*paths],check=True);subprocess.run(['git','-C',str(source),'add','--',*paths],check=True);subprocess.run(['git','-C',str(source),'commit','--only','-m','media: camss: own per-frame IPE colour programs in the request parcel','--',*paths],check=True,capture_output=True);assert not git('status','--porcelain')
d=dict(stage=397,parent=parent,source=str(source),branch=git('branch','--show-current'),commit=git('rev-parse','HEAD'),changed=paths,clean=True,installed=False,old_job_frame_and_owner_layouts_unchanged=True,reset_release_and_unknown_completion_cleanup_unchanged=True,new_api='camss_a5_ipe_run_colour_status')
(HERE/'source-state.json').write_text(json.dumps(d,indent=2)+'\n');(HERE/'build-intree.py').write_text((HERE.parent/'kernel396/build-intree.py').read_text().replace('stage=396','stage=397'));print(json.dumps(d,indent=2))
