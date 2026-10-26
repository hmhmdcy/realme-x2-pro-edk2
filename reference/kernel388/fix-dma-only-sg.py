from pathlib import Path
import difflib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;relative=Path('drivers/media/platform/qcom/camss')
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');mount=importlib.util.module_from_spec(spec);spec.loader.exec_module(mount)
source=mount.mounted_build().parent/'source354';state=json.loads((HERE/'source-state.json').read_text())
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
assert git('rev-parse','HEAD')==state['commit'] and not git('status','--porcelain')
helper=(HERE/'camss-icp-a5-dma.c').read_bytes();(source/relative/'camss-icp-a5-dma.c').write_bytes(helper);(P/'camss-icp-a5-dma.c.proposed').write_bytes(helper)
name='camss-icp-a5-m2m.c';p=source/relative/name;s=p.read_text()
def replace(a,b):
 global s
 assert s.count(a)==1,(a,s.count(a));s=s.replace(a,b)
replace('u32 users;','u32 users;\n\tint first_error;')
replace('\telse if (ret)\n\t\tdev->failed++;','\telse if (ret) {\n\t\tdev->failed++;\n\t\tif (!dev->first_error)\n\t\t\tdev->first_error = ret;\n\t\tdev_info(dev->a5->dev, "IPE m2m job failed ret=%d\\n", ret);\n\t}')
replace('"\\\"direct_completed\\\":%llu,\\\"cancelled\\\":%llu,\\\"failed\\\":%llu,\\\"starts\\\":%llu,\\\"stops\\\":%llu}\\n",','"\\\"first_error\\\":%d,\\\"direct_completed\\\":%llu,\\\"cancelled\\\":%llu,\\\"failed\\\":%llu,\\\"starts\\\":%llu,\\\"stops\\\":%llu}\\n",')
replace('\t\t(unsigned long long)dev->direct_completed,','\t\tdev->first_error, (unsigned long long)dev->direct_completed,')
p.write_text(s);(P/(name+'.proposed')).write_text(s)
git('diff','--check');git('add','--',str(relative/'camss-icp-a5-dma.c'),str(relative/name));git('commit','-m','media: camss: validate DMA aliases without reading exporter SG pages')
state.update(commit=git('rev-parse','HEAD'),dmabuf_debug_dma_only_tables_supported=True)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
patch=''
for leaf in state['changed']:
 a=(P/(leaf+'.before')).read_text();b=(P/(leaf+'.proposed')).read_text()
 patch+=''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='a/'+str(relative/leaf) if a else '/dev/null',tofile='b/'+str(relative/leaf)))
(HERE/'direct-dma.patch').write_text(patch)
print(json.dumps(state,indent=2))
