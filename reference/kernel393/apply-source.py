from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
for n in ['transfer','adapter']:assert json.loads((HERE/(n+'-validation.json')).read_text())['passed']
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
assert git('rev-parse','HEAD')=='a3c2b4cfacad2eefaadd4ef3efd35de3d9244d07' and not git('status','--porcelain')
names=json.loads((HERE/'proposal-validation.json').read_text())['changed'];relative='drivers/media/platform/qcom/camss/'
for n in names:assert (source/relative/n).read_bytes()==(P/(n+'.before')).read_bytes()
subprocess.run(['git','-C',str(source),'checkout','-b','samurai-ipe-errors393'],check=True,capture_output=True)
for n in names:(source/relative/n).write_bytes((P/(n+'.proposed')).read_bytes())
paths=[relative+n for n in names]
subprocess.run(['git','-C',str(source),'diff','--check','--',*paths],check=True)
subprocess.run(['git','-C',str(source),'add','--',*paths],check=True)
subprocess.run(['git','-C',str(source),'commit','--only','-m','media: camss: isolate proven preflight IPE job rejections','--',*paths],check=True,capture_output=True)
assert not git('status','--porcelain')
r=dict(stage=393,parent='a3c2b4cfacad2eefaadd4ef3efd35de3d9244d07',source=str(source),branch=git('branch','--show-current'),commit=git('rev-parse','HEAD'),changed=paths,sha256={n:hashlib.sha256((source/relative/n).read_bytes()).hexdigest() for n in names},clean=True,installed=False)
(HERE/'source-state.json').write_text(json.dumps(r,indent=2)+'\n')
build=(HERE.parent/'kernel389/build-intree.py').read_text().replace('stage=389','stage=393')
start=build.index('modules=[camss/');end=build.index('\ncommand=',start)
build=build[:start]+"modules=[camss/'qcom-camss-icp-a5-core.ko',camss/'camss-icp-a5-m2m.ko']\nruntime_modules=set(modules)\nmodules += [v4l2/'v4l2-mem2mem.ko',v4l2/'v4l2-isp.ko']\nmodules += [vb2/(n+'.ko') for n in ['videobuf2-common','videobuf2-v4l2','videobuf2-memops','videobuf2-vmalloc','videobuf2-dma-sg']]"+build[end:]
build=build.replace("normal_camss_and_icp_same_module_owner=True,","normal_camss_and_icp_same_module_owner=True,only_changed_core_adapter_pair_selected_for_deployment=True,")
(HERE/'build-intree.py').write_text(build)
print(json.dumps(r))
