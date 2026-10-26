"""Exercise a private scene estimate via public metadata; no installed tuning change."""
from pathlib import Path
import hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent
profile=json.loads((host.PRIVATE/'scene-profile-candidate-private.json').read_text());assert not profile['factory_or_dark_calibrated'] and not profile['install_as_device_tuning']
s=(HERE/'samurai-blc.c').read_text()
s=s.replace('2104','1632').replace('1560','1224').replace('1052','816').replace('820560','499392').replace('410280','249696')
s=s.replace('s5k3m5 ','imx319 ').replace('MEDIA_BUS_FMT_SGRBG10_1X10','MEDIA_BUS_FMT_SRGGB10_1X10')
s=s.replace('static volatile sig_atomic_t interrupted;','static volatile sig_atomic_t interrupted;\nstatic unsigned scene_r,scene_b,scene_black;')
s=s.replace('if(argc!=3||strcmp(argv[1],"--pattern"))','if(argc!=6||strcmp(argv[1],"--scene"))')
needle=' struct utsname identity;';idx=s.index(needle)
s=s[:idx]+''' scene_r=strtoul(argv[3],NULL,10);scene_b=strtoul(argv[4],NULL,10);scene_black=strtoul(argv[5],NULL,10);
 if(scene_r>4096||scene_b>4096||scene_black>8192)return 2;
'''+s[idx:]
a=s.index(' static const unsigned levels[7]');b=s.index(' struct camss_params_aec_bhist',a)
s=s[:a]+''' if(phase==1||phase==2||phase==3||phase==5||phase==6)wb.g_sub=wb.b_sub=wb.r_sub=scene_black;
 if(phase==2||phase==3||phase==5||phase==6){wb.r_gain=scene_r;wb.b_gain=scene_b;}
 if(phase==5)wb.header.flags=0;
 if(phase==4){wb.header.flags=V4L2_ISP_PARAMS_FL_BLOCK_DISABLE;wb.header.size=sizeof(wb.header);}
'''+s[b:]
s=s.replace('exposure.minimum>150||exposure.maximum<1200||gain.minimum>64||gain.maximum<64','exposure.minimum>3000||exposure.maximum<3000||gain.minimum>512||gain.maximum<768')
s=s.replace('off.value=2','off.value=0').replace('V4L2_CID_ANALOGUE_GAIN,.value=64','V4L2_CID_ANALOGUE_GAIN,.value=512').replace('V4L2_CID_EXPOSURE,.value=150','V4L2_CID_EXPOSURE,.value=3000')
s=s.replace('gain_code=64 exposures=150,1200,150 sensor_tpg=2','gain_code=512,768 exposure=3000 sensor_tpg=0')
s=s.replace('  if(frame&&frame%9==0){','  if(frame==27){struct v4l2_control a={.id=V4L2_CID_ANALOGUE_GAIN,.value=768};if(call(sensor,VIDIOC_S_CTRL,&a))goto cleanup;puts("ANALOGUE_GAIN_CHANGE code=768");}\n  if(frame&&frame%9==0){')
p=HERE/'samurai-scene.c';assert not p.exists();p.write_text(s)
binary=host.PRIVATE/'scene-aarch64-private'
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-D__counted_by(x)=','-D__EXPORTED_HEADERS__','-static','-s','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include','-I/home/cy122/x2pro-linux/camera279-isp-kernel/include/uapi',str(p),'-o',str(binary)],capture_output=True)
(host.PRIVATE/'scene-probe-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
assert subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True).returncode==0
for name in ['native-blc.py','launch-blc.py','poll-blc.py']:
 t=(HERE/name).read_text().replace('blc','scene')
 if name=='native-blc.py':
  args=[str(profile['gains_q10_rgb'][0]),str(profile['gains_q10_rgb'][2]),str(profile['black_u16'])]
  t=t.replace("'--pattern',str(root/'frame-private')","'--scene',str(root/'frame-private'),"+','.join(repr(v) for v in args))
  t=t.replace("physical_sensor='s5k3m5',sensor_pattern=2","physical_sensor='imx319',sensor_pattern=0,scene_estimate_only=True,dark_calibrated=False,installed_tuning_unchanged=True")
 (HERE/name.replace('blc','scene')).write_text(t)
(HERE/'scene-tool-validation.json').write_text(json.dumps(dict(stage=298,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),binary_bytes=binary.stat().st_size,strict_compile_pass=True,not_run_on_phone=True,scene_estimate_only=True,no_installed_tuning_change=True,black_u16=profile['black_u16'],gains_q10_rgb=profile['gains_q10_rgb'],analogue_gain_codes=[512,768],exposure_code=3000),indent=2)+'\n')
print('Prepared bounded IMX319 BLS/WB/gain experiment; scene estimates remain uncalibrated.')
