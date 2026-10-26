from pathlib import Path
import host,json,sys
here=Path(__file__).resolve().parent;assert sys.argv[1:] in [['helper'],['lut']];variant=sys.argv[1]
assert json.loads((here/(variant+'-candidate-staging-validation.json')).read_text())['isolated_candidate_staged']
capture=(here.parent/'kernel211/capture-user-libcamera.py').read_text().replace('k211-runtime','k213-baseline').replace("root/'k211-user-libcamera'","root/'k213-user-libcamera-"+variant+"'").replace("runtime/'samurai-camera-211'","runtime/'samurai-camera-213-"+variant+"'").replace('stage=211','stage=213').replace("'--capture=3'","'--capture=6'").replace('three_rgb_frames_captured','six_rgb_frames_captured').replace('len(frames)==3','len(frames)==6')
capture=capture.replace("'LIBCAMERA_LOG_LEVELS':'*:INFO'", "'LIBCAMERA_LOG_LEVELS':'*:INFO,Debayer:DEBUG,IPASoft:DEBUG'")
capture=capture.replace('hist=collections.Counter(pixels[::max(1,len(pixels)//65536)])','hist=collections.Counter(pixels)').replace('sample_entropy_bits=','entropy_bits=')
capture=capture.replace('nonconstant=len(hist)>1)', 'nonconstant=len(hist)>1,all_rgb_bytes_zero=hist.get(0,0)==len(pixels),mean_rgb_byte=round(sum(k*n for k,n in hist.items())/total,6),std_rgb_byte=round(math.sqrt(max(0,sum(k*k*n for k,n in hist.items())/total-(sum(k*n for k,n in hist.items())/total)**2)),6))')
capture=capture.replace("args=['/usr/bin/cam'", "prefix=Path('/run/samurai-camera213-"+variant+"')\nenv.update(LD_LIBRARY_PATH=str(prefix/'usr/lib'),LIBCAMERA_IPA_MODULE_PATH=str(prefix/'usr/lib/libcamera/ipa'),LIBCAMERA_IPA_PROXY_PATH=str(prefix/'usr/libexec/libcamera'),LIBCAMERA_IPA_CONFIG_PATH=str(prefix/'usr/share/libcamera/ipa'))\nargs=[str(prefix/'usr/bin/cam')")
code=r'''
from pathlib import Path
import json,subprocess,re,os
os.umask(0o077);root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k213-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
variant=VARIANT;fixture=root/('k213-capture-fixture-'+variant);fixture.mkdir(mode=0o700)
nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='imx471 7-0010'];assert len(nodes)==1;node='/dev/'+nodes[0].name
names=['exposure','analogue_gain','digital_gain','vertical_blanking']
def controls():
    p=subprocess.run(['v4l2-ctl','-d',node,'--get-ctrl='+','.join(names)],capture_output=True,text=True,timeout=10);assert p.returncode==0
    return {k:int(v) for k,v in re.findall(r'(\w+):\s*(-?\d+)',p.stdout)}
saved=controls();assert set(saved)==set(names);(fixture/'controls-before-private.json').write_text(json.dumps(saved,indent=2)+'\n')
try:
    exec(CAPTURE)
finally:
    subprocess.run(['v4l2-ctl','-d',node,'--set-ctrl=vertical_blanking='+str(saved['vertical_blanking'])],capture_output=True,check=True,timeout=10)
    subprocess.run(['v4l2-ctl','-d',node,'--set-ctrl='+','.join(k+'='+str(saved[k]) for k in names if k!='vertical_blanking')],capture_output=True,check=True,timeout=10)
restored=controls();assert restored==saved
report['variant']=variant
report['room_lights_off_user_confirmed']=True
report['all_rgb_bytes_examined_not_only_a_sample']=True
report['rgb_all_zero_alone_is_not_a_bug_diagnosis']=True
report['source_lut_fix_included']=variant=='lut'
report['sensor_controls_restored']=True
report['first_frame_nonconstant']=bool(frames and frames[0]['nonconstant'])
report['nonconstant_frame_count']=sum(f['nonconstant'] for f in frames)
report['helper_warning_absent']='Failed to create camera sensor helper for imx471' not in stderr.decode(errors='replace')
report['static_properties_warning_absent']="No static properties available for 'imx471'" not in stderr.decode(errors='replace')
report['analogue_gain_metadata']=[float(x) for x in re.findall(r'AnalogueGain = ([0-9.]+)',stdout.decode(errors='replace'))]
report['gain_limits']=[line for line in stderr.decode(errors='replace').splitlines() if 'IPASoft' in line and 'Exposure ' in line]
report['debayer_params']=[line for line in stderr.decode(errors='replace').splitlines() if 'Debayer parameters:' in line]
report['new_faults_zero']=not any(faults.values())
report['system_camera_libraries_not_replaced']=True
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');(fixture/'summary.json').write_text(json.dumps(dict(controls_restored=True,variant=variant),indent=2)+'\n')
print(json.dumps({'candidate_capture':report}))
'''.replace('VARIANT',repr(variant)).replace('CAPTURE',repr(capture))
p=host.ssh('python3 -',input=code.encode(),timeout=100);(host.PRIVATE/(variant+'-capture-host-private.log')).write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout.splitlines()[-1])['candidate_capture'];(here/(variant+'-capture-validation.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
