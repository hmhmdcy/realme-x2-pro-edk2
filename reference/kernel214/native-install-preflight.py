from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
for tag in ['isolated-dark-raw','isolated-white-raw','isolated-white-rgb']:
    result=json.loads((here/(tag+'-validation.json')).read_text());assert result['program_exit']==0 and result['taint']==0 and not any(result['fault_delta'].values()) and result['camera_devices_suspended'] and result['error_line_count']==0
code=r'''
from pathlib import Path
import hashlib,json,os,stat,subprocess
os.umask(0o077);base=Path('/var/lib/samurai/k214-baseline');stage=Path('/var/lib/samurai/k214-package-candidates');out=Path('/var/lib/samurai/k214-package-transaction');out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(base/'boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert Path('/lib/apk/db/installed').read_bytes()==(base/'apk-installed-before-private.txt').read_bytes()
original=json.loads((base/'original-files-manifest-private.json').read_text());manifest=json.loads((stage/'forward-manifest.json').read_text())
new_paths=[]
for package in manifest['packages']:
    for relative,item in package['files'].items():
        p=Path('/')/relative
        if relative not in original:
            assert not p.exists() and not p.is_symlink(),relative;new_paths.append(relative);continue
        old=original[relative]
        if old['kind']=='symlink':assert p.is_symlink() and os.readlink(p)==old['target']
        else:assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==old['sha256'] and stat.S_IMODE(p.stat().st_mode)==old['mode']
repo=Path('/etc/apk/repositories.d/60-samurai-camera.list');assert not repo.exists()
repositories={}
for p in [Path('/etc/apk/repositories'),*sorted(Path('/etc/apk/repositories.d').glob('*'))]:
    if p.is_file():repositories[str(p)]=dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.read_bytes().hex(),mode=stat.S_IMODE(p.stat().st_mode))
(out/'repositories-before-private.json').write_text(json.dumps(repositories,indent=2)+'\n')
(out/'world-before-private.txt').write_bytes(Path('/etc/apk/world').read_bytes())
(out/'installed-before-private.txt').write_bytes(Path('/lib/apk/db/installed').read_bytes())
(out/'new-paths-private.json').write_text(json.dumps(new_paths,indent=2)+'\n')
private_repos=out/'candidate-repositories.list';private_repos.write_text('ndx file://'+str(stage/'forward/packages.adb')+'\n')
cmd=['apk','--no-network','--repositories-file',str(private_repos),'add','--simulate','samurai-camera-stack=0.1.0-r0']
p=subprocess.run(cmd,capture_output=True,text=True,timeout=30);(out/'native-forward-dry-private.log').write_text(p.stdout+p.stderr);assert p.returncode==0
actions=[line for line in p.stdout.splitlines() if line.startswith('(')];assert len(actions)==7
for name in ['libcamera','libcamera-ipa','libcamera-tools']:assert any(('Upgrading '+name+' (99990.7.2-r4 -> 99990.7.2-r5)') in line for line in actions)
for name in ['libcamera-gstreamer','libcamera-v4l2','samurai-camera-config','samurai-camera-stack']:assert any(('Installing '+name+' (') in line for line in actions)
files={}
for pattern in ['/etc/user/init.d/*wire*','/etc/user/init.d/*pipe*','/etc/xdg/autostart/*wire*','/etc/xdg/autostart/*pipe*','/etc/xdg/autostart/*samurai*','/usr/share/gnome-session/sessions/*phosh*','/usr/share/applications/*wireplumber*','/usr/share/applications/*pipewire*']:
    import glob
    for name in glob.glob(pattern):
        path=Path(name)
        if path.is_file():files[name]=path.read_text(errors='replace')
pcms={str(p):p.read_text() for p in Path('/proc/asound').glob('card*/pcm*/sub*/status')}
supervisors=[]
for p in Path('/proc').iterdir():
    if not p.name.isdigit():continue
    try:
        comm=(p/'comm').read_text().strip()
        if comm in ['supervise-daemon','s6-supervise','runsv','wireplumber','pipewire']:
            supervisors.append(dict(pid=int(p.name),comm=comm,argv=[s.decode(errors='replace') for s in (p/'cmdline').read_bytes().split(b'\0') if s]))
    except OSError:pass
(out/'session-context-private.json').write_text(json.dumps(dict(files=files,pcms=pcms,processes=supervisors),indent=2)+'\n')
assert Path('/lib/apk/db/installed').read_bytes()==(base/'apk-installed-before-private.txt').read_bytes()
report=dict(stage=214,native_phone_solver_passed=True,three_upgrades_and_four_additions_only=True,all_existing_affected_paths_match_saved_baseline=True,new_payload_path_count=len(new_paths),new_paths_previously_absent=True,original_repository_files_database_and_world_saved=True,same_boot_and_taint_zero=True,supervisor_context_collected=True,pcm_status=[text.strip() for text in pcms.values()],user_session_service_files_found=sorted(files),package_transaction_not_sent=True)
(out/'preflight-summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=60);(host.PRIVATE/'native-preflight-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'native-install-preflight-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
