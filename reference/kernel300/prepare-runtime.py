"""Prepare a public-API application and bounded private IPA worker workflow."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess
import host
HERE=Path(__file__).resolve().parent;old=HERE.parent/'kernel299'
s=(old/'pipeline-smoke.cpp').read_text()
needle='\tCameraManager manager;';assert s.count(needle)==1
s=s.replace(needle,'\tstd::cout << "APPLICATION_PROCESS pid=" << getpid() << std::endl;\n'+needle)
needle='\t\t\tconst auto &m = buffer->metadata();';assert s.count(needle)==1
s=s.replace(needle,needle+'''
\t\t\tauto gains = request->metadata().get(controls::ColourGains);
\t\t\tif (!gains || std::abs((*gains)[0] - 2.22f) > 0.0001f || std::abs((*gains)[1] - 1.90f) > 0.0001f)
\t\t\t\t++failed;
\t\t\telse std::cout << "APPLICATION_IPA_METADATA request=" << request->sequence() << " colour_gains_valid=1" << std::endl;''')
s=s.replace('#include <chrono>','#include <chrono>\n#include <cmath>')
(HERE/'pipeline-smoke.cpp').write_text(s)
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');stage=SDK/'private/camss300-runtime';stage.mkdir(exist_ok=True)
shutil.copyfile(HERE/'pipeline-smoke.cpp',stage/'pipeline-smoke.cpp')
q=subprocess.run(['chroot',str(SDK),'/usr/bin/g++','-std=c++20','-O0','-Wall','-Wextra','-Werror',
 '-I/candidate278-r24/usr/include/libcamera','/private/camss300-runtime/pipeline-smoke.cpp',
 '-L/candidate278-r24/usr/lib','-Wl,-rpath-link,/candidate278-r24/usr/lib','-lcamera','-lcamera-base','-pthread','-o','/private/camss300-runtime/pipeline-smoke'],capture_output=True,timeout=180)
(host.PRIVATE/'application-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
shutil.copyfile(stage/'pipeline-smoke',host.PRIVATE/'pipeline-smoke-aarch64-private')
previous=host.PRIVATE.parent/'kernel299/pipeline-fixture-aarch64-private'
expected=json.loads((old/'inline-smoke-tools-validation.json').read_text())['binaries']['pipeline-fixture-aarch64-private']['sha256']
assert hashlib.sha256(previous.read_bytes()).hexdigest()==expected
shutil.copyfile(previous,host.PRIVATE/'pipeline-fixture-aarch64-private')
s=(old/'native-inline.py').read_text().replace('k299-inline','k300-ipa').replace('stage=299','stage=300')
needle="LIBCAMERA_LOG_LEVELS='*:WARN,CamssVfe:DEBUG'";assert s.count(needle)==1
s=s.replace(needle,"LIBCAMERA_IPA_MODULE_PATH=str(stage/'ipa'),LIBCAMERA_IPA_PROXY_PATH=str(stage/'proxy'),LIBCAMERA_IPA_FORCE_ISOLATION='1',LIBCAMERA_LOG_LEVELS='*:WARN,CamssVfe:DEBUG,IPACamss:DEBUG,IPAManager:DEBUG,IPAProxy:DEBUG'")
needle=" report['passed']=";n=s.index(needle)
s=s[:n]+''' app_pids=set(map(int,re.findall(r'APPLICATION_PROCESS pid=(\\d+)',text)))
 ipa_pids=set(map(int,re.findall(r'IPA init pid=(\\d+)',text)))
 stats_pids=set(map(int,re.findall(r'IPA stats pid=(\\d+)',text)))
 ipa_live=[]
 for pid in ipa_pids:
  p=Path('/proc',str(pid),'stat')
  if p.exists() and p.read_text().rsplit(')',1)[1].split()[0]!='Z':
   cmd=Path('/proc',str(pid),'cmdline').read_bytes()
   if str(stage).encode() in cmd:ipa_live.append(pid)
 report.update(ipa_isolation_forced=True,application_pids=sorted(app_pids),ipa_pids=sorted(ipa_pids),ipa_statistics_process_pids=sorted(stats_pids),ipa_workers_still_live=ipa_live,
  ipa_metadata_frames=len(re.findall(r'APPLICATION_IPA_METADATA ',text)),ipa_metadata_reports_logical_startup_colour_gains=True,
  manual_hardware_ipa_integrated=True,full_ipa_and_automatic_algorithms_not_implemented=True)
'''+s[n:]
needle=" (root/'summary-private.json').write_text";n=s.index(needle)
s=s[:n]+" report['passed']=report['passed'] and len(app_pids)==1 and len(ipa_pids)==1 and not app_pids.intersection(ipa_pids) and stats_pids==ipa_pids and not ipa_live and report['ipa_metadata_frames']==72\n"+s[n:]
(HERE/'native-ipa.py').write_text(s)
for name in ['launch-inline.py','poll-inline.py']:
 s=(old/name).read_text().replace('k299-inline','k300-ipa').replace('native-inline.py','native-ipa.py')
 s=s.replace('inline-bundle','ipa-bundle').replace('inline-capture','ipa-capture').replace('inline-','ipa-')
 if name.startswith('launch-'):
  s=re.sub(r'write_text\(json.dumps\(receipt\).*?;print', 'write_text(json.dumps(receipt)+chr(10));print', s)
 # Stage299's correction only belongs to its original selector experiment.
 if name.startswith('poll-'):
  a=s.index("if run=='r1' and");b=s.index("if report['state']['terminal']",a);s=s[:a]+s[b:]
 (HERE/name.replace('inline','ipa')).write_text(s)
report=dict(stage=300,public_application_werror_compile_pass=True,requires72_colour_gains_metadata_responses=True,
 private_ipa_module_proxy_path_and_forced_isolation_configured=True,prior_state_restoring_fixture_reused_with_verified_hash=True,
 application_source_sha256=hashlib.sha256((HERE/'pipeline-smoke.cpp').read_bytes()).hexdigest(),application_sha256=hashlib.sha256((host.PRIVATE/'pipeline-smoke-aarch64-private').read_bytes()).hexdigest())
(HERE/'runtime-tools-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
subprocess.run(['python3',str(HERE/'enable-runtime-modes.py')],check=True)
if (HERE/'prepare-fixture.py').exists():
 subprocess.run(['python3',str(HERE/'prepare-fixture.py')],check=True)
 p=HERE/'runtime-tools-validation.json';report=json.loads(p.read_text());report.update(prior_state_restoring_fixture_reused_with_verified_hash=False,updated_two_phase_graph_fixture_used=True);p.write_text(json.dumps(report,indent=2)+'\n')
