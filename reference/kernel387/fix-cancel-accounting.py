from pathlib import Path
import difflib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');mount=importlib.util.module_from_spec(spec);spec.loader.exec_module(mount)
kernel=mount.mounted_build().parent/'source354';git=lambda *a:subprocess.check_output(['git','-C',str(kernel),*a],text=True).strip()
state=json.loads((HERE/'source-state.json').read_text());assert git('rev-parse','HEAD')==state['commit'] and not git('status','--porcelain')
name='drivers/media/platform/qcom/camss/camss-icp-a5-m2m.c';p=kernel/name;before=p.read_text();after=before
def replace(a,b):
 global after
 assert after.count(a)==1,(a,after.count(a));after=after.replace(a,b)
replace('u64 jobs, completed, failed, starts, stops;','u64 jobs, completed, cancelled, failed, starts, stops;')
replace('\tif (ret)\n\t\tdev->failed++;\n\telse\n\t\tdev->completed++;','\tif (ret == -ECANCELED)\n\t\tdev->cancelled++;\n\telse if (ret)\n\t\tdev->failed++;\n\telse\n\t\tdev->completed++;')
replace('"\\\"failed\\\":%llu,\\\"starts\\\":%llu,\\\"stops\\\":%llu}\\n",','"\\\"cancelled\\\":%llu,\\\"failed\\\":%llu,\\\"starts\\\":%llu,\\\"stops\\\":%llu}\\n",')
replace('\t\t(unsigned long long)dev->failed, (unsigned long long)dev->starts,','\t\t(unsigned long long)dev->cancelled, (unsigned long long)dev->failed,\n\t\t(unsigned long long)dev->starts,')
p.write_text(after);git('diff','--check');(HERE/'cancel-accounting.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+name,tofile='b/'+name)))
git('add','--',name);git('commit','-m','media: qcom: distinguish IPE stream cancellation from processing errors')
state.update(commit=git('rev-parse','HEAD'),kernel_change='stable_media_driver_and_separate_cancel_counter');(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
# Test the exact accounting statements, including a real error after cancellation.
a=after.index('\tif (ret == -ECANCELED)\n\t\tdev->cancelled++;');b=after.index('\n\tmutex_unlock',a);body=after[a:b]
code='#include <assert.h>\n#include <errno.h>\nstruct counters {unsigned completed,cancelled,failed;};\nstatic void account(struct counters *dev,int ret){\n'+body+'\n}\nint main(void){struct counters d={0};account(&d,0);account(&d,-ECANCELED);account(&d,-EIO);assert(d.completed==1 && d.cancelled==1 && d.failed==1);return 0;}\n'
model=host.PRIVATE/'cancel-accounting.c';model.write_text(code)
q=subprocess.run(['cc','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-no-pie',str(model),'-o',str(host.PRIVATE/'cancel-accounting')],capture_output=True);assert not q.returncode,q.stderr.decode()
q=subprocess.run([str(host.PRIVATE/'cancel-accounting')],capture_output=True);assert not q.returncode,q.stderr.decode()
(HERE/'cancel-validation.json').write_text(json.dumps(dict(stage=387,actual_accounting_statements=True,success_cancel_error_separate=True,real_errors_not_ignored=True,asan_ubsan=True,passed=True),indent=2)+'\n');print(json.dumps(state))
