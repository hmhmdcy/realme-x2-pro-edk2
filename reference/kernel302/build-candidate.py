"""Build302 against the preserved SDK without replaying earlier source installers."""
from pathlib import Path
import hashlib,json,os,shutil,signal,subprocess,sys
import host
HERE=Path(__file__).resolve().parent;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');tree=SDK/'work/libcamera299-inline'
assert (HERE/'baseline-preservation-validation.json').exists()
def put(source,target):
 if not target.exists() or source.read_bytes()!=target.read_bytes():shutil.copyfile(source,target)
for name,source in [('include/libcamera/ipa/camss.mojom',HERE/'camss.mojom')]:put(source,tree/name)
for directory,target in [('ipa','src/ipa/camss-vfe'),('pipeline','src/libcamera/pipeline/camss-vfe')]:
 for source in (HERE/directory).glob('*'):put(source,tree/target/source.name)
attempt=1
while (host.PRIVATE/f'build-r{attempt}-private.log').exists():attempt+=1
proc=subprocess.Popen(['chroot',str(SDK),'/usr/bin/ninja','-C','/work/libcamera299-inline/output','-j8'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
try:out,err=proc.communicate(timeout=1200)
except subprocess.TimeoutExpired:
 os.killpg(proc.pid,signal.SIGTERM)
 try:out,err=proc.communicate(timeout=15)
 except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);out,err=proc.communicate()
(host.PRIVATE/f'build-r{attempt}-private.log').write_bytes(out+err);print((out+err).decode()[-6500:])
names=['include/libcamera/ipa/camss.mojom','src/ipa/camss-vfe/camss.cpp','src/libcamera/pipeline/camss-vfe/camss_vfe.cpp']
report=dict(stage=302,kernel_build=298,attempt=attempt,build_exit=proc.returncode,isolated_source=str(tree),not_installed=True,
 uses_existing_sensor_helper_and_delayed_controls=True,metadata_from_per_sof_snapshot=True,automatic_algorithms_not_implemented=True,
 source_sha256={n:hashlib.sha256((tree/n).read_bytes()).hexdigest() for n in names})
(HERE/'build-validation.json').write_text(json.dumps(report,indent=2)+'\n');sys.exit(proc.returncode)
