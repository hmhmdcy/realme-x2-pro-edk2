"""Diagnostic-only CPU/rusage endpoints around unchanged focus statistics."""
from pathlib import Path
import difflib,hashlib,json,shutil
import host,storage
HERE=Path(__file__).resolve().parent;volume=storage.mount.mounted_build().parent
old=volume/'libcamera446-focus-workspace';new=storage.candidate();assert old.is_dir() and not new.exists()
shutil.copytree(old,new,symlinks=True,ignore=lambda d,n:[s for s in n if s=='pkg' or s.startswith('pkg-before') or s=='__pycache__'])
tree=new/'src/libcamera-v0.7.2';header='src/libcamera/pipeline/camss-vfe/hardware_focus.h';pipeline='src/libcamera/pipeline/camss-vfe/camss_vfe.cpp'
original={n:(old/'src/libcamera-v0.7.2'/n).read_text() for n in [header,pipeline]};text=original[header]
def replace(a,b):
 global text
 assert text.count(a)==1,(a,text.count(a));text=text.replace(a,b)
replace('#include <sys/ioctl.h>','#include <sys/ioctl.h>\n#include <sys/resource.h>\n#include <sched.h>\n#include <time.h>')
replace('struct FocusMeasurementTiming {','''struct FocusExecutionSnapshot {
 int64_t cpuNs=0;long minor=0,major=0,voluntary=0,involuntary=0;int cpu=-1;bool valid=false;
};
inline FocusExecutionSnapshot focusExecutionSnapshot()
{
 FocusExecutionSnapshot result;timespec cpu{};rusage usage{};
 if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&cpu) || getrusage(RUSAGE_THREAD,&usage))return result;
 result.cpuNs=int64_t(cpu.tv_sec)*1000000000+cpu.tv_nsec;
 result.minor=usage.ru_minflt;result.major=usage.ru_majflt;
 result.voluntary=usage.ru_nvcsw;result.involuntary=usage.ru_nivcsw;
 result.cpu=sched_getcpu();result.valid=result.cpu>=0;return result;
}

struct FocusMeasurementTiming {''')
replace('int64_t syncStartUs=0,mapUs=0,sampleUs=0,scoreUs=0,unmapUs=0,syncEndUs=0;', '''int64_t syncStartUs=0,mapUs=0,sampleUs=0,scoreUs=0,unmapUs=0,syncEndUs=0;
 int64_t sampleCpuUs=0;long sampleMinor=0,sampleMajor=0,sampleVoluntary=0,sampleInvoluntary=0;
 int sampleCpuBefore=-1,sampleCpuAfter=-1;bool sampleExecutionValid=false;''')
replace('   const auto statistics=measureLumaFocus(', '   const auto usageBefore=focusExecutionSnapshot();\n   const auto statistics=measureLumaFocus(')
replace('   measured.sampleUs=elapsed();', '''   const auto usageAfter=focusExecutionSnapshot();
   measured.sampleUs=elapsed();
   measured.sampleExecutionValid=usageBefore.valid && usageAfter.valid && usageAfter.cpuNs>=usageBefore.cpuNs;
   if(measured.sampleExecutionValid){
    measured.sampleCpuUs=(usageAfter.cpuNs-usageBefore.cpuNs)/1000;
    measured.sampleMinor=usageAfter.minor-usageBefore.minor;measured.sampleMajor=usageAfter.major-usageBefore.major;
    measured.sampleVoluntary=usageAfter.voluntary-usageBefore.voluntary;measured.sampleInvoluntary=usageAfter.involuntary-usageBefore.involuntary;
    measured.sampleCpuBefore=usageBefore.cpu;measured.sampleCpuAfter=usageAfter.cpu;
   }''')
(tree/header).write_text(text);(HERE/'hardware_focus.h').write_text(text)
text=original[pipeline]
replace('<<" unmap-us="<<focusTiming.unmapUs<<" sync-end-us="<<focusTiming.syncEndUs;', '''<<" unmap-us="<<focusTiming.unmapUs<<" sync-end-us="<<focusTiming.syncEndUs;
  LOG(CamssVfe,Debug)<<"FOCUS_EXECUTION epoch="<<frameEpoch<<" sof="<<sequence<<" valid="<<focusTiming.sampleExecutionValid
   <<" sample-wall-us="<<focusTiming.sampleUs<<" sample-cpu-us="<<focusTiming.sampleCpuUs
   <<" minor="<<focusTiming.sampleMinor<<" major="<<focusTiming.sampleMajor
   <<" voluntary="<<focusTiming.sampleVoluntary<<" involuntary="<<focusTiming.sampleInvoluntary
   <<" cpu-before="<<focusTiming.sampleCpuBefore<<" cpu-after="<<focusTiming.sampleCpuAfter;''')
(tree/pipeline).write_text(text)
(HERE/'0059-camss-focus-execution-observations.patch').write_text(''.join(''.join(difflib.unified_diff(original[n].splitlines(True),(tree/n).read_text().splitlines(True),fromfile='a/'+n,tofile='b/'+n)) for n in [header,pipeline]))
state=json.loads((HERE.parent/'kernel446/source-state.json').read_text())
for row in state['source_hashes']:row['sha256']=hashlib.sha256((tree/row['path']).read_bytes()).hexdigest()
state.update(stage=447,source=str(tree),baseline_stage=446,source_baseline_stage=446,changed_this_stage=[header,pipeline],build_pending=True,diagnostic_only=True)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(dict(stage=447,source=str(tree),diagnostic_only=True,phone_changed=False,passed=True)))
