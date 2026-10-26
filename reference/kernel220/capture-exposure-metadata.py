"""Metadata-only finite capture; numerical controls, no image mapping or files."""
from pathlib import Path
import host,json,sys
here=Path(__file__).resolve().parent
assert len(sys.argv) in [3,4]
width,height=map(int,sys.argv[1:3]);assert (width,height) in [(1920,1088),(2296,1728),(4608,3456)]
flavour=sys.argv[3] if len(sys.argv)==4 else 'r6';assert flavour in ['r6','candidate-threaded','candidate-isolated','system-r7']
assert not (width==4608 and flavour in ['r6','candidate-isolated'])
cell=2 if width==4608 else 1;tag=f'exposure-metadata-{flavour}-{width}x{height}'
code=(here.parent/'kernel219/native-mode-runner.py').read_text()
code=code.replace("k219-runtime/boot-id-private.txt","k220-baseline/boot-id-private.txt")
code=code.replace("tag=f'{width}x{height}-{kind}-pattern{pattern}-{library}'",'tag='+repr(tag)).replace("'k219-capture-'","'k220-capture-'")
code=code.replace("[(2304,1728,1)","[(1920,1088,1),(2304,1728,1)")
code=code.replace("LIBCAMERA_LOG_LEVELS='*:INFO'", "LIBCAMERA_LOG_LEVELS='*:INFO,DelayedControls:DEBUG'")
code=code.replace("LIBCAMERA_LOG_LEVELS='*:INFO,DelayedControls:DEBUG'", "LIBCAMERA_LOG_LEVELS='*:INFO,DelayedControls:DEBUG,IPAManager:DEBUG'")
library='system'
if flavour.startswith('candidate-'):
 library='candidate';profile='config-full' if width==4608 else 'config-isolated' if flavour=='candidate-isolated' else 'config-default'
 code=code.replace("prefix=Path('/run/samurai-camera219-cpu')","prefix=Path('/run/samurai-camera220-r7')")
 code=code.replace("prefix/'config-enabled'",'prefix/'+repr(profile))
 code=code.replace("LIBCAMERA_IPA_MODULE_PATH='/usr/lib/libcamera/ipa',LIBCAMERA_IPA_PROXY_PATH='/usr/libexec/libcamera',LIBCAMERA_IPA_CONFIG_PATH='/usr/share/libcamera/ipa'", "LIBCAMERA_IPA_MODULE_PATH=str(prefix/'usr/lib/libcamera/ipa'),LIBCAMERA_IPA_PROXY_PATH=str(prefix/'usr/libexec/libcamera'),LIBCAMERA_IPA_CONFIG_PATH=str(prefix/'usr/share/libcamera/ipa')")
elif flavour=='system-r7' and width==4608:
 code=code.replace('def demote():',"env['XDG_CONFIG_HOME']='/run/samurai-camera220-r7/config-full'\ndef demote():")
code=code.replace("names=['exposure','analogue_gain','digital_gain','vertical_blanking','test_pattern']","names=['exposure','analogue_gain','digital_gain','vertical_blanking','test_pattern','horizontal_blanking','pixel_rate']")
old="process=subprocess.Popen(['/run/samurai-camera219-probes/native-mode-probe',sensor,kind,str(pattern),str(width),str(height),str(cell)],env=env,preexec_fn=demote,stdout=subprocess.PIPE,stderr=subprocess.PIPE)"
args=['cam','--camera','/base/soc@0/cci@ac4b000/i2c-bus@1/camera@10',f'--stream=role=viewfinder,width={width},height={height},pixelformat=RGB888','--capture=36','--metadata']
assert code.count(old)==1;code=code.replace(old,'process=subprocess.Popen('+repr(args)+',env=env,preexec_fn=demote,stdout=subprocess.PIPE,stderr=subprocess.PIPE)')
marker='    try:stdout,stderr=process.communicate(timeout=25)'
assert code.count(marker)==1
code=code.replace(marker,"    active_controls=controls()\n"+marker)
old="data=json.loads(stdout) if process.returncode==0 else None"
new="""exposures=[int(n) for n in re.findall(r'^\\s*ExposureTime = (\\d+)\\s*$',stdout.decode(),re.M)]
lines=[int(n) for n in re.findall(r'Reading Exposure to (\\d+) at index',stderr.decode())]
data=dict(width=width,height=height,stride=None,frames=stdout.count(b'seq:')) if process.returncode==0 else None"""
assert code.count(old)==1;code=code.replace(old,new)
code=code.replace("frames=data['frames'] if data else []", "frame_count=data['frames'] if data else 0,exposure_metadata_microseconds=exposures,delayed_exposure_lines=lines,active_controls=active_controls")
code=code.replace('dma_sync_read_start_end=True,','dma_sync_read_start_end=False,no_cpu_pixel_buffer_access=True,')
code=code.replace('report=dict(stage=219,','report=dict(stage=220,metadata_only=True,ipa_isolation_forced_observed=b\'forced through configuration\' in stderr,')
compile(code,'native-exposure-metadata220','exec')
p=host.ssh(f'python3 - rgb 0 {width} {height} {cell} {library}',input=code.encode(),timeout=90)
(host.PRIVATE/(tag+'-host-private.log')).write_bytes(p.stdout+p.stderr)
r=json.loads(p.stdout)
if r['program_exit']==0:
 sensor_width=1928 if width==1920 else 2304 if width==2296 else width
 c=r['active_controls'];line_us=(sensor_width+c['horizontal_blanking'])*1000000/c['pixel_rate']
 observed=r['exposure_metadata_microseconds'];lines=r['delayed_exposure_lines']
 r.update(validation_flavour=flavour,sensor_line_duration_us=line_us,
          expected_exposure_microseconds=[n*line_us for n in lines[:len(observed)]],
          maximum_metadata_conversion_error_us=max(abs(v-n*line_us) for v,n in zip(observed,lines)))
(here/(tag+'-validation.json')).write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({k:v for k,v in r.items() if k not in ['exposure_metadata_microseconds','delayed_exposure_lines','expected_exposure_microseconds']}))
assert r['program_exit']==0 and r['frame_count']==36 and len(r['exposure_metadata_microseconds'])==36
assert r['all_formats_restored'] and r['media_graph_restored'] and r['sensor_controls_restored'] and r['camera_devices_suspended']
assert r['taint']==0 and not any(r['fault_delta'].values())
if flavour!='r6':assert len(r['delayed_exposure_lines'])>=36 and r['maximum_metadata_conversion_error_us']<1
if flavour=='candidate-isolated':assert r['ipa_isolation_forced_observed']
