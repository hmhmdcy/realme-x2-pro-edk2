from pathlib import Path
import hashlib,importlib.util,json,shlex,subprocess
import host,storage
HERE=Path(__file__).resolve().parent;state=json.loads((HERE/'source-state.json').read_text())
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');mount=importlib.util.module_from_spec(s);s.loader.exec_module(mount)
source=mount.mounted_build().parent/'source354';git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
assert git('rev-parse','HEAD')==state['commit'] and not git('status','--porcelain')
library=storage.candidate()/'src/libcamera-v0.7.2';baseline=storage.previous.candidate()/'src/libcamera-v0.7.2'
for leaf in ['camss_ipe.h','camss_ipe.cpp']:
 assert (library/'src/libcamera/pipeline/camss-vfe'/leaf).read_bytes()==(HERE/leaf).read_bytes()
assert (library/'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp').read_bytes()==(HERE/'camss-vfe-after.cpp').read_bytes()
for relative in ['src/libcamera/pipeline_handler.cpp','src/ipa/camss-vfe/camss.cpp']:
 assert (library/relative).read_bytes()==(baseline/relative).read_bytes()
code="""from pathlib import Path
import json
def live(root,key,name):
 state=json.loads((root/'state.json').read_text());p=Path('/proc')/str(state.get(key,-1))
 try:return str(root/name).encode() in (p/'cmdline').read_bytes() and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z'
 except OSError:return False
nodes=[p for p in Path('/sys/class/video4linux').glob('video*') if (p/'name').read_text().strip()=='qcom-ipe-a5']
media=[p for p in Path('/sys/bus/media/devices').glob('media*') if any(parent.name=='ac10000.samurai-icp356-boot' for parent in p.resolve().parents)]
services={name:[] for name in ['pipewire','wireplumber']}
for p in Path('/proc').glob('[0-9]*'):
 try:
  n=(p/'comm').read_text().strip()
  if n in services and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z':services[n].append(int(p.name))
 except OSError:pass
print(json.dumps(dict(taint=int(Path('/proc/sys/kernel/tainted').read_text()),kernel=Path('/proc/sys/kernel/osrelease').read_text().strip(),
 workers=[dict(run=root.name,worker=live(root,'pid','worker.py'),collector=live(root,'collector_pid','snapshot-collector.py'),client=live(root,'client_pid','camera-client.py')) for root in Path('/var/lib/samurai').glob('k387-pipeline-r*')],
 camera_pm={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['acb3000.camss','ac4a000.cci','ac4b000.cci']},
 candidates_absent=not any(Path('/sys/module',n).exists() for n in ['qcom_camss_icp_a5_core','camss_icp_a5_boot_test','camss_icp_a5_m2m','v4l2_mem2mem']),
 m2m_video_absent=not nodes,m2m_media_absent=not media,services=services,
 rails={(p/'name').read_text().strip():dict(state=(p/'state').read_text().strip(),users=int((p/'num_users').read_text())) for p in Path('/sys/class/regulator').glob('regulator.*') if (p/'name').read_text().startswith(('cam-main-','cam-front-','cam-rear-','cam-tele-'))},
 temporary_firmware_absent=not Path('/lib/firmware/qcom/sm8150/samurai-icp356.elf').exists(),
 static_icp_status=Path('/sys/firmware/devicetree/base/soc@0/icp@ac10000/status').read_bytes().rstrip(b'\\0').decode())))
"""
d=json.loads(host.ssh('python3 -c '+shlex.quote(code),timeout=25).stdout)
assert d['taint']==0 and all(v=='suspended' for v in d['camera_pm'].values()) and all(d[k] for k in ['candidates_absent','m2m_video_absent','m2m_media_absent','temporary_firmware_absent'])
assert d['static_icp_status']=='disabled' and len(d['rails'])==9 and all(v==dict(state='disabled',users=0) for v in d['rails'].values())
assert d['workers'] and not any(any(row[k] for k in ['worker','collector','client']) for row in d['workers'])
assert all(len(pids)==1 for pids in d['services'].values())
report=dict(stage=387,source_commit=state['commit'],source_clean=True,actual_source_matches_proposal=True,ipa_and_dispatcher_unchanged=True,guard378_verified=True,
 candidate_permanently_installed=False,ssc_issue_not_fixed=True,**d,passed=True)
(HERE/'current-state-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
