"""Build the standard IPA module/proxy in the isolated SDK candidate only."""
from pathlib import Path
import difflib,hashlib,json,os,shutil,signal,subprocess,sys,tarfile
import host
HERE=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');tree=SDK/'work/libcamera299-inline'
assert (host.PRIVATE/'tested299-source-private.tar.gz').is_file()
def put(p,data):
 if isinstance(data,str):data=data.encode()
 if not p.exists() or p.read_bytes()!=data:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
with tarfile.open(host.PRIVATE/'tested299-source-private.tar.gz') as archive:
 def original(name):return archive.extractfile(name).read().decode()
 changes={}
 name='meson_options.txt';old=original(name);assert "choices : ['ipu3', 'mali-c55'" in old
 new=old.replace("choices : ['ipu3', 'mali-c55'","choices : ['camss-vfe', 'ipu3', 'mali-c55'",1);put(tree/name,new);changes[name]=(old,new)
 name='include/libcamera/ipa/meson.build';old=original(name);needle='pipeline_ipa_mojom_mapping = {';assert old.count(needle)==1
 new=old.replace(needle,needle+"\n    'camss-vfe': 'camss.mojom',");put(tree/name,new);changes[name]=(old,new)
put(tree/'include/libcamera/ipa/camss.mojom',(HERE/'camss.mojom').read_bytes())
for p in (HERE/'pipeline').glob('*'):put(tree/'src/libcamera/pipeline/camss-vfe'/p.name,p.read_bytes())
for name in ['parameter_encoder.cpp','parameter_encoder.h','params.h']:
 p=tree/'src/libcamera/pipeline/camss-vfe'/name
 if p.exists():p.unlink()
for p in (HERE/'ipa').glob('*'):put(tree/'src/ipa/camss-vfe'/p.name,p.read_bytes())
for name in ['parameter_encoder.cpp','parameter_encoder.h','params.h']:
 data=(HERE.parent/'kernel299/ipa'/name).read_text()
 if name=='params.h':data=data.replace('#include "v4l2_params.h"','#include "../libipa/v4l2_params.h"')
 put(tree/'src/ipa/camss-vfe'/name,data)
(HERE/'ipa-build-integration.patch').write_text(''.join(''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='a/'+n,tofile='b/'+n)) for n,(a,b) in changes.items()))
attempt=1
while (host.PRIVATE/f'meson-r{attempt}-private.log').exists():attempt+=1
options=json.loads((tree/'output/meson-info/intro-buildoptions.json').read_text())
if 'camss-vfe' not in next(o for o in options if o['name']=='ipas')['choices']:
 q=subprocess.run(['chroot',str(SDK),'/usr/bin/meson','setup','--reconfigure','/work/libcamera299-inline/output','/work/libcamera299-inline'],capture_output=True,timeout=180)
 (host.PRIVATE/f'meson-refresh-r{attempt}-private.log').write_bytes(q.stdout+q.stderr)
 if q.returncode:print((q.stdout+q.stderr).decode()[-5000:]);sys.exit(q.returncode)
args=['chroot',str(SDK),'/usr/bin/meson','setup','--reconfigure','/work/libcamera299-inline/output','/work/libcamera299-inline','-Dipas=camss-vfe,simple','-Dwerror=true']
q=subprocess.run(args,capture_output=True,timeout=180);(host.PRIVATE/f'meson-r{attempt}-private.log').write_bytes(q.stdout+q.stderr)
if q.returncode:print((q.stdout+q.stderr).decode()[-5000:]);sys.exit(q.returncode)
proc=subprocess.Popen(['chroot',str(SDK),'/usr/bin/ninja','-C','/work/libcamera299-inline/output','-j8'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
try:stdout,stderr=proc.communicate(timeout=1200)
except subprocess.TimeoutExpired:
 os.killpg(proc.pid,signal.SIGTERM)
 try:stdout,stderr=proc.communicate(timeout=15)
 except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);stdout,stderr=proc.communicate()
(host.PRIVATE/f'build-r{attempt}-private.log').write_bytes(stdout+stderr);print((stdout+stderr).decode()[-6500:])
names=['include/libcamera/ipa/camss.mojom','src/libcamera/pipeline/camss-vfe/camss_vfe.cpp','src/ipa/camss-vfe/camss.cpp','src/ipa/camss-vfe/parameter_encoder.cpp']
report=dict(stage=300,kernel_build=298,attempt=attempt,build_exit=proc.returncode,isolated_source=str(tree),not_installed=True,
 actual_generated_ipa_interface_proxy_and_worker=True,configuration_and_parameter_encoding_and_statistics_in_ipa=True,
 automatic_algorithms_not_implemented=True,physical_validation_pending=True,
 source_sha256={n:hashlib.sha256((tree/n).read_bytes()).hexdigest() for n in names})
(HERE/'build-validation.json').write_text(json.dumps(report,indent=2)+'\n');sys.exit(proc.returncode)
