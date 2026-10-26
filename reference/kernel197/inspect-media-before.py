from pathlib import Path
import gzip,json,os,re,shutil,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k197-media-before-r2';out.mkdir(mode=0o700);assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k197-baseline/boot-id-private.txt').read_bytes()
p=Path('/sys/bus/platform/devices/acb3000.camss');assert p.exists() and (p/'driver').exists();driver=(p/'driver').resolve();config=gzip.decompress(Path('/proc/config.gz').read_bytes()).decode();selected=[s for s in config.splitlines() if any(s.startswith('CONFIG_'+n+'=') for n in ['VIDEO_QCOM_CAMSS','VIDEO_DEV','V4L2_FWNODE'])]
users=[]
for process in Path('/proc').iterdir():
 if not process.name.isdecimal():continue
 try:
  for fd in (process/'fd').iterdir():
   try:target=os.readlink(fd)
   except OSError:continue
   if any(target.startswith('/dev/'+n) for n in ['video','media','v4l-subdev']):users.append(dict(pid=int(process.name),fd=fd.name,target=target))
 except (OSError,PermissionError):continue
(out/'video-users-private.json').write_text(json.dumps(users,indent=2)+'\n');tools={n:shutil.which(n) for n in ['media-ctl','v4l2-ctl','cam']};media=[]
for device in sorted(Path('/dev').glob('media*')) if tools['media-ctl'] else []:
 result=subprocess.run(['media-ctl','-d',str(device),'-p'],capture_output=True,text=True,timeout=15);(out/(device.name+'-topology-private.txt')).write_text(result.stdout+result.stderr);assert result.returncode==0
 media.append(dict(device=device.name,entities=re.findall(r'- entity (\d+): ([^\n]+)',result.stdout)))
report=dict(stage=197,camss_driver=driver.name,camss_driver_path=str(driver),camss_is_module=(driver/'module').exists(),camss_config=selected,active_video_fd_count=len(users),tools=tools,media=media)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
