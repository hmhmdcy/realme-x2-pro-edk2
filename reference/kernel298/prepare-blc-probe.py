"""Prepare a standard metadata BLS sweep from the shared-SOF regression tool."""
from pathlib import Path
import hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel297/samurai-stats-r2.c').read_text().replace('k297','k298').replace('#297 ','#298 ')
a=s.index(' if(phase==1||phase==5||phase==6)');b=s.index(' struct camss_params_aec_bhist',a)
s=s[:a]+''' static const unsigned levels[7]={0,4096,8192,16384,0,8192,8192};
 wb.g_sub=wb.b_sub=wb.r_sub=levels[phase<7?phase:0];
 if(phase==5)wb.header.flags=0;
 if(phase==6){wb.r_gain=2048;wb.b_gain=1536;}
 if(phase==4){wb.header.flags=V4L2_ISP_PARAMS_FL_BLOCK_DISABLE;wb.header.size=sizeof(wb.header);}
'''+s[b:]
p=HERE/'samurai-blc.c';assert not p.exists();p.write_text(s)
for name in ['native-stats-r2.py','launch-stats-r2.py','poll-stats-r2.py']:
 t=(HERE.parent/'kernel297'/name).read_text().replace('297','298')
 t=t.replace('stats-r2','blc').replace('stats_r2','blc')
 # Keep original ROI/lifecycle expectations and all failure records.
 (HERE/name.replace('stats-r2','blc')).write_text(t)
binary=host.PRIVATE/'blc-aarch64-private'
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-D__counted_by(x)=','-D__EXPORTED_HEADERS__','-static','-s',
 '-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include','-I/home/cy122/x2pro-linux/camera279-isp-kernel/include/uapi',str(p),'-o',str(binary)],capture_output=True)
(host.PRIVATE/'blc-probe-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
assert subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True).returncode==0
assert subprocess.run(['qemu-aarch64',str(binary),'--pattern','/tmp/not-used'],capture_output=True).returncode==3
(HERE/'blc-tool-validation.json').write_text(json.dumps(dict(stage=298,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),binary_bytes=binary.stat().st_size,strict_compile_pass=True,wrong_kernel_guard_pass=True,not_run_on_phone=True,empty_event_enoent_supported=True,black_levels_u16=[0,4096,8192,16384],no_dark_scene_required_for_sensor_pattern=True),indent=2)+'\n')
print('BLC standard metadata probe compiled; self-test and wrong-kernel guard passed.')
