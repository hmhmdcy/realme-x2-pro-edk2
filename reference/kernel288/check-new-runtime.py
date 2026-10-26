"""Read the new kernel's module identities, processed node and idle PM state."""
from pathlib import Path
import json
import host

ROOT=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import hashlib,json,os,struct,subprocess
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k288-work/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#288 ')
root=Path('/var/lib/samurai/k288-runtime-check');assert not root.exists();root.mkdir(mode=0o700)
kernel=subprocess.check_output(['dmesg']);(root/'dmesg-private.txt').write_bytes(kernel)
graph=subprocess.check_output(['media-ctl','-d','/dev/media0','-p'],text=True);(root/'graph-private.txt').write_text(graph)
def note(p):
 b=Path(p).read_bytes();offset=struct.unpack_from('<Q',b,40)[0];size,count,index=struct.unpack_from('<HHH',b,58)
 sec=[struct.unpack_from('<IIQQQQIIQQ',b,offset+i*size) for i in range(count)];names=b[sec[index][4]:sec[index][4]+sec[index][5]]
 return next(b[s[4]:s[4]+s[5]] for s in sec if names[s[0]:].split(b'\0',1)[0]==b'.note.gnu.build-id')
modules={}
for name in ['qcom_camss','i2c_qcom_cci','s5k3m5','s5kgw1','imx319','imx471','lc898219xi','qcom_pm8008','qcom_pm8008_regulator']:
 p=Path(subprocess.check_output(['modinfo','-n',name],text=True).strip())
 match=Path('/sys/module',name,'notes/.note.gnu.build-id').read_bytes()==note(p);assert match,name
 modules[name]=dict(loaded_note_matches_disk=match,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
node=subprocess.check_output(['media-ctl','-d','/dev/media0','-e','msm_vfe0_video3'],text=True).strip()
formats=subprocess.check_output(['v4l2-ctl','-d',node,'--list-formats-ext'],text=True)
assert "'NV12'" in formats and formats.count("[0]")==1 and "[1]" not in formats
(root/'formats-private.txt').write_text(formats)
pm={p.name:(p/'power/runtime_status').read_text().strip() for p in Path('/sys/bus/i2c/devices').glob('*') if p.name in ['6-0010','8-002d','7-0010','9-0010','6-0072']}
report=dict(stage=288,kernel_build=288,release=os.uname().release,modules=modules,
            pix_capture_node=node,pix_formats=formats,loaded_module_notes_match=True,
            runtime_taint=int(Path('/proc/sys/kernel/tainted').read_text()),sensor_pm=pm,
            pstore_files=len(list(Path('/sys/fs/pstore').glob('*'))),
            diagnostics={k:kernel.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu_fault=b'gpu fault:',dsp_fatal=b'fatal error received').items()},
            services={name:subprocess.run(['rc-service',name,'status'],capture_output=True).returncode==0 for name in ['greetd','samurai-ssc','iio-sensor-proxy']},
            no_hardware_image_yet=True)
(root/'summary-private.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=30)
(host.PRIVATE/'postboot-runtime-private.json').write_bytes(q.stdout)
report=json.loads(q.stdout)
(ROOT/'postboot-runtime-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
