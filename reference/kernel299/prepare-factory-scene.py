"""Compare factory and scene-derived residual black on the physical IMX319."""
from pathlib import Path
import hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent
old=json.loads((host.PRIVATE.parent/'kernel298/scene-profile-candidate-private.json').read_text());assert not old['factory_or_dark_calibrated']
r,b=old['gains_q10_rgb'][0],old['gains_q10_rgb'][2]
nr,nb=(r*1088+512)//1024,(b*1088+512)//1024
s=(HERE/'samurai-factory-bls.c').read_text()
a=s.index(' if(phase>=1&&phase<=3)');z=s.index(' struct params_envelope envelope=',a)
s=s[:a]+f''' wb.r_gain={r};wb.b_gain={b};
 if(phase>=1&&phase<=3||phase==5)wb.g_sub=wb.b_sub=wb.r_sub=3840;
 if(phase==2||phase==3||phase==5){{wb.g_gain=1088;wb.r_gain={nr};wb.b_gain={nb};}}
 if(phase==3)wb.g_sub=wb.b_sub=wb.r_sub=4096;
 if(phase==4){{wb.header.flags=V4L2_ISP_PARAMS_FL_BLOCK_DISABLE;wb.header.size=sizeof(wb.header);}}
 struct camss_params_aec_bhist bh={{.header={{CAMSS_PARAMS_AEC_BHIST,V4L2_ISP_PARAMS_FL_BLOCK_ENABLE,sizeof(bh)}},.width=1632,.height=1224}};
'''+s[z:]
s=s.replace('if(phase>=1&&phase<=3||phase==5)','if((phase>=1&&phase<=3)||phase==5)')
s=s.replace('s5k3m5 ','imx319 ').replace('MEDIA_BUS_FMT_SGRBG10_1X10','MEDIA_BUS_FMT_SRGGB10_1X10').replace('2104','1632').replace('1560','1224').replace('820560','499392')
s=s.replace('exposure.minimum>150||exposure.maximum<1200||gain.minimum>64||gain.maximum<64','exposure.minimum>3000||exposure.maximum<3000||gain.minimum>768||gain.maximum<768')
s=s.replace('off.value=2','off.value=0').replace('V4L2_CID_ANALOGUE_GAIN,.value=64','V4L2_CID_ANALOGUE_GAIN,.value=768').replace('V4L2_CID_EXPOSURE,.value=150','V4L2_CID_EXPOSURE,.value=3000')
s=s.replace('gain_code=64 exposures=150,1200,150 sensor_tpg=2','gain_code=768 exposure=3000 sensor_tpg=0').replace('"--pattern"','"--capture"')
p=HERE/'samurai-factory-scene.c';assert not p.exists();p.write_text(s)
binary=host.PRIVATE/'factory-scene-aarch64-private'
q=subprocess.run(['aarch64-linux-gnu-gcc','-std=gnu11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-D__counted_by(x)=','-D__EXPORTED_HEADERS__','-static','-s','-I/mnt/e/edk2-samurai-out/kernel288/host-uapi/include','-I/home/cy122/x2pro-linux/camera279-isp-kernel/include/uapi',str(p),'-o',str(binary)],capture_output=True)
(host.PRIVATE/'factory-scene-compile-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
assert subprocess.run(['qemu-aarch64',str(binary),'--self-test'],capture_output=True).returncode==0
assert subprocess.run(['qemu-aarch64',str(binary),'--capture','/tmp/not-used'],capture_output=True).returncode==3
for name in ['native-factory-bls.py','launch-factory-bls.py','poll-factory-bls.py']:
 t=(HERE/name).read_text().replace('factory-bls','factory-scene')
 if name.startswith('native-'):
  t=t.replace("'--pattern'","'--capture'").replace("physical_sensor='s5k3m5',sensor_pattern=2","physical_sensor='imx319',sensor_pattern=0,scene_wb_estimate_only=True,no_individual_dark_calibration=True,no_tuning_install=True")
 if name.startswith('launch-'):t=t.replace('assert not root.exists();root.mkdir(mode=0o700);','assert root.is_dir();')
 (HERE/name.replace('factory-bls','factory-scene')).write_text(t)
(HERE/'factory-scene-tool-validation.json').write_text(json.dumps(dict(stage=299,kernel_build=298,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),binary_bytes=binary.stat().st_size,strict_compile_pass=True,wrong_kernel_guard_pass=True,planned_frames=54,
 old_scene_wb_q10_rgb=[r,1024,b],normalized_scene_wb_q10_rgb=[nr,1088,nb],scene_wb_is_not_factory_or_calibrated=True,analogue_gain_code=768,exposure_code=3000),indent=2)+'\n')
print('Compiled IMX319 controlled black-offset and explicit-normalization comparison.')
