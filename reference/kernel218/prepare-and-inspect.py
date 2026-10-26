from pathlib import Path
import hashlib,host,json,shutil
here=Path(__file__).resolve().parent;private=host.PRIVATE;private.mkdir(mode=0o700)
shutil.copyfile(private.parent/'kernel217/usb-ipv6-candidates-private.json',private/'usb-ipv6-candidates-private.json')
code=r'''
from pathlib import Path
import hashlib,json,os,shutil
os.umask(0o077);root=Path('/var/lib/samurai');base=root/'k218-baseline';assert not base.exists()
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k217-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and os.uname().version.startswith('#183 ')
assert Path('/sys/firmware/devicetree/base/model').read_bytes()==b'Realme X2 Pro (RMX1931CN)\0'
assert all(Path(p,'power/runtime_status').read_text().strip()=='suspended' for p in ['/sys/bus/i2c/devices/7-0010','/sys/bus/platform/devices/acb3000.camss','/sys/bus/platform/devices/ac4b000.cci'])
module=Path('/usr/lib/modules')/os.uname().release/'kernel/drivers/media/i2c/imx471.ko';assert hashlib.sha256(module.read_bytes()).hexdigest()=='1388a070e9c902e6b23b3896ce1f50f8f0e44f68d5243ed73e897dcaee186a5b'
base.mkdir(mode=0o700);(base/'boot-id-private.txt').write_bytes(boot);shutil.copyfile(module,base/'imx471-original.ko')
db=Path('/lib/apk/db/installed').read_bytes();assert db==(root/'k217-baseline/installed-before-private.txt').read_bytes();(base/'installed-before-private.txt').write_bytes(db)
mem={line.split(':',1)[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemAvailable:','CmaTotal:','CmaFree:'))}
report=dict(stage=218,fresh_same217_boot_verified=True,current_r5_database_and216_module_unchanged=True,camera_suspended=True,taint=0,memory_budget_bytes=mem,no_device_install_flash_or_reboot=True)
(base/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=45);(private/'baseline-host-private.log').write_bytes(p.stdout+p.stderr);report=json.loads(p.stdout);(here/'baseline-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
root=Path('/home/cy122/x2pro-linux/libcamera214-root');original=root/'work/libcamera/src/libcamera-v0.7.2';target=root/'work/libcamera218';assert not target.exists()
shutil.copytree(original,target,ignore=shutil.ignore_patterns('output','__pycache__','.git'))
assert not any(p.suffix=='.pem' or p.name.startswith('ipa-priv-key.') for p in target.rglob('*') if p.is_file())
selected=['src/libcamera/software_isp/debayer_cpu.cpp','src/libcamera/software_isp/debayer_cpu.h','src/libcamera/software_isp/software_isp.cpp','src/libcamera/pipeline/simple/simple.cpp','include/libcamera/internal/software_isp/debayer.h','include/libcamera/internal/sensor_cfa_layout.h']
contexts={}
for name in selected:
    path=target/name
    if not path.exists():continue
    lines=path.read_text().splitlines();chosen=set()
    for index,line in enumerate(lines):
        if any(word in line for word in ['DebayerCpu::configure','process2','process4','process0','processFrame','queueBuffers','processTask','Task','quadBayer','CellCollapse','DebayerCpu(','SwStatsCpu(','Debayer::configure','DmaBufAllocator','exportFrameBuffers','exportBuffers','Raw','inputBuffers_','inputBuffers','createBuffers','sensorCfaLayout']):chosen.update(range(max(0,index-3),min(len(lines),index+14)))
    contexts[name]=dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),lines={str(i+1):lines[i] for i in sorted(chosen)})
(private/'cpu-integration-context-private.json').write_text(json.dumps(contexts,indent=2)+'\n')
kernel=Path('/home/cy122/pmos-samurai-kernel136/kernel');matches={}
for name in ['include/uapi/linux/videodev2.h','include/uapi/linux/media-bus-format.h']:
    lines=(kernel/name).read_text().splitlines();matches[name]=[line for line in lines if any(word in line.lower() for word in ['quad','4x4','qrggb','qbggr','qgbrg','qgrbg'])]
(private/'quad-uapi-search-private.json').write_text(json.dumps(matches,indent=2)+'\n');print(json.dumps(dict(isolated_source_copy=str(target),quad_uapi_matches=matches)))
