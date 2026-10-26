"""Test fresh tiny-ROI statistics after an independently stopped metadata stream."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel296')
assert not (P/'stats-r2-launch-private.json').exists()
s=(ROOT/'samurai-stats.c').read_text()
needle='if((frame==0||frame==72||frame==90)&&sum!=820560)';assert needle in s
s=s.replace(needle,'if(((frame==0||frame==72)&&sum!=820560)||(frame==90&&sum!=2))')
needle='stats_streaming=false;puts("STATS_STREAMOFF_IMAGE_CONTINUES");'
assert needle in s
s=s.replace(needle,needle+'''
    if(queue_params(3,true)||call(params_fd,VIDIOC_STREAMON,&params_type))goto cleanup;params_streaming=true;
    if(dequeue_params(3))goto cleanup;puts("PARAMS_RESTART_TINY_ROI_STATS_STOPPED");''',1)
p=ROOT/'samurai-stats-late.c';assert not p.exists();p.write_text(s)
binary=P/'stats-late-aarch64-private'
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-D__counted_by(x)=','-D__EXPORTED_HEADERS__','-static','-s','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include','-I/home/cy122/x2pro-linux/camera279-isp-kernel/include/uapi',str(p),'-o',str(binary)],capture_output=True)
(P/'stats-late-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
assert subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True,timeout=10).returncode==0
assert subprocess.run(['qemu-aarch64',str(binary),'--pattern','/tmp/wrong-kernel'],capture_output=True,timeout=10).returncode==3
(ROOT/'stats-late-tool-validation.json').write_text(json.dumps(dict(stage=296,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),binary_bytes=binary.stat().st_size,strict_compile_pass=True,wrong_kernel_guard_pass=True,late_roi_change_while_stats_stopped=True,first_late_population_required=2,not_run_on_phone=True),indent=2)+'\n')
p=ROOT/'native-stats-r2.py';s=p.read_text().replace('k296-tools/stats\'','k296-tools/stats-late\'').replace("report['parameter_completions']==7","report['parameter_completions']==8")
assert 'k296-tools/stats-late' in s;compile(s,str(p),'exec');p.write_text(s)
s=(ROOT/'launch-stats.py').read_text().replace("'stats-tool-validation.json'","'stats-late-tool-validation.json'").replace("'stats-aarch64-private'","'stats-late-aarch64-private'").replace('k296-tools/stats','k296-tools/stats-late').replace('native-stats.py','native-stats-r2.py').replace('k296-stats-r1','k296-stats-r2').replace('stats-launch-private.json','stats-r2-launch-private.json').replace('stats-worker-private.log','stats-r2-worker-private.log')
needle="proof=json.loads((ROOT/'stats-late-tool-validation.json').read_text());"
assert needle in s;s=s.replace(needle,"assert json.loads((ROOT/'statistics-pixel-validation.json').read_text())['passed']\nassert json.loads((ROOT/'optical-statistics-validation.json').read_text())['all_packets_valid']\n"+needle)
p=ROOT/'launch-stats-r2.py';compile(s,str(p),'exec');p.write_text(s)
p=ROOT/'analyze-statistics-r2.py';s=p.read_text().replace('820560,None,820560]','820560,None,2]')
s=s.replace("expected_sum=820560,valid=r['sum']==820560","expected_sum=2 if r['frame']==90 else 820560,valid=r['sum']==(2 if r['frame']==90 else 820560)")
compile(s,str(p),'exec');p.write_text(s)
print('Prepared second sensor-switch run with a new tiny ROI before late stats start; no kernel/device changes.')
