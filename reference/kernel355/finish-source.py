from pathlib import Path
import hashlib,importlib.util,json,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
for name in ['resources-validation.json','intree-build-validation.json','power-runtime-r2-validation.json']:assert json.loads((HERE/name).read_text())['passed'],name
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';base='drivers/media/platform/qcom/camss/'
p=source/base/'Kconfig';s=p.read_text().replace('depends on VIDEO_QCOM_CAMSS && IOMMU_DMA\n','depends on VIDEO_QCOM_CAMSS && IOMMU_DMA && OF && PM_GENERIC_DOMAINS\n');p.write_text(s)
for name in ['Kconfig','Makefile']:shutil.copyfile(source/base/name,HERE/'kernel'/name)
names=['Kconfig','Makefile','camss-icp-a5-resources.h','camss-icp-a5-resources.c','camss-icp-a5-power-test.c'];paths=[base+n for n in names]
for path in (HERE/'kernel').glob('*'):assert path.read_bytes()==(source/base/path.name).read_bytes(),path.name
assert (HERE/'camss-icp-a5-power-test.c').read_bytes()==(source/base/'camss-icp-a5-power-test.c').read_bytes()
subprocess.run(['git','-C',str(source),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(source),'diff','--cached','--check'],check=True)
pending=subprocess.check_output(['git','-C',str(source),'diff','--cached','--name-only'],text=True).splitlines()
if pending:
 assert set(pending)<=set(paths)
 q=subprocess.run(['git','-C',str(source),'commit','-m','media: camss: manage SM8150 A5 BPS and IPE resources'],capture_output=True);(P/'source-commit.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
commit=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip();parent='ea71fa4fd8375502d73231dfb749cbd3a23920eb'
patch=subprocess.check_output(['git','-C',str(source),'diff',parent,commit,'--',*paths]);(HERE/'a5-icp-resources.patch').write_bytes(patch)
status=subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True);assert not status,status
state=dict(stage=355,source=str(source),branch='samurai-icp-a5-resources355',commit=commit,parent=parent,tracked_clean=True,reuses_preceding_checkout=True,
 files=[dict(path=p,sha256=hashlib.sha256((source/p).read_bytes()).hexdigest()) for p in paths],temporary_overlay_blob_not_in_source_or_patch=True,
 resources_hardware_tested=True,firmware_not_started=True,installed=False)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
print(json.dumps(dict(commit=commit,files=len(paths),patch_bytes=len(patch),tracked_clean=True),indent=2))
