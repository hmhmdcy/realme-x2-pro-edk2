"""Compile strict-k294 probes and prepare bounded workers; no device operations."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'kernel293'
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel294')
for tag in ['stats','optical']:
 p=ROOT/('samurai-'+tag+'.c');binary=PRIVATE/(tag+'-aarch64-private')
 q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-D__counted_by(x)=','-D__EXPORTED_HEADERS__','-static','-s','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include','-I/home/cy122/x2pro-linux/camera279-isp-kernel/include/uapi',str(p),'-o',str(binary)],capture_output=True)
 (PRIVATE/(tag+'-compile-private.log')).write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
 assert subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True,timeout=10).returncode==0
 assert subprocess.run(['qemu-aarch64',str(binary),'--pattern' if tag=='stats' else '--capture','/tmp/wrong-kernel-k294'],capture_output=True,timeout=10).returncode==3
 proof=dict(stage=294,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),binary_bytes=binary.stat().st_size,strict_compile_pass=True,wrong_kernel_guard_pass=True,not_run_on_phone=True)
 (ROOT/(tag+'-tool-validation.json')).write_text(json.dumps(proof,indent=2)+'\n')
s=(OLD/'native-wb-params.py').read_text().replace('k293','k294').replace('stage=293','stage=294').replace('kernel_build=293','kernel_build=294').replace("'#293 '","'#294 '").replace('wb-params','stats')
s=s.replace("report['actual_frames']==81","report['actual_frames']==99").replace('len(images)==9','len(images)==11')
s=s.replace(" report['passed']=ret==0", " report['statistics']= [dict((k,int(v,16) if k=='hash' else int(v)) for k,v in re.findall(r'(\\w+)=([0-9a-f]+)',line)) for line in text.splitlines() if line.startswith('STATS frame=')]\n report['statistics_frames']=len(report['statistics'])\n report['stats_restart_markers']=all(x in text for x in ['IMAGE_REOPEN_WITHOUT_PARAMS_STATS_STILL_STREAMING','STATS_STREAMOFF_IMAGE_CONTINUES','STATS_LATE_STREAMON_IMAGE_CONTINUES'])\n report['passed']=report['statistics_frames']==90 and report['stats_restart_markers'] and ret==0")
# All values on STATS lines are integers; the hash is the only hex field.
(ROOT/'native-stats.py').write_text(s);compile(s,'native-stats.py','exec')
for name in ['launch-wb-params.py','poll-wb-params.py']:
 s=(OLD/name).read_text().replace('k293','k294').replace('stage=293','stage=294').replace('wb-params','stats')
 p=ROOT/name.replace('wb-params','stats');assert not p.exists();p.write_text(s);compile(s,str(p),'exec')
print('Compiled independent stats/optical probes and generated bounded stats worker.')
