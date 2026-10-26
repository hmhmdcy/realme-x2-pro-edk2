from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
code=(here.parent/'kernel210/final-health.py').read_text().replace('k210','k212').replace('stage=210','stage=212')
start=code.index("capture=json.loads(");end=code.index("sensor=Path(",start)
code=code[:start]+"capture=json.loads((root/'k212-user-libcamera-r2/summary.json').read_text())\nassert capture['post_warmup_four_rgb_frames_nonconstant'] and capture['system_configuration_opened'] and capture['no_cpu_mode_environment_override'] and capture['no_drm_device_opened'] and capture['taint']==0 and capture['new_faults_zero']\nassert len(capture['frames'])==6 and capture['black_startup_frame_indices']==[0]\n"+code[end:]
code=code.replace("tools=tools,libcamera_packages=", "tools=tools,libcamera_packages=")
code=code.replace('wireplumber_resumed=True,','desktop_camera_monitor_not_paused=True,')
code=code.replace("assert len(rails)==2", "assert sensor.joinpath('of_node/power-domains').read_bytes()==cci.joinpath('of_node/power-domains').read_bytes()\nassert len(rails)==2")
code=code.replace("report=dict(stage=212,", "configuration=Path('/etc/libcamera/configuration.yaml');assert configuration.parent.stat().st_mode&0o777==0o755 and configuration.stat().st_mode&0o777==0o644\nreport=dict(stage=212,system_cpu_config_readable=True,default_cpu_capture_post_warmup_pass=True,first_frame_black_still_open=True,")
p=host.ssh('python3 -',input=code.encode(),timeout=60);(host.PRIVATE/'final-health-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'final-health-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
