#!/usr/bin/env python3
"""Prepare a new, isolated pmbootstrap workspace; never flashes a device."""
from pathlib import Path
import argparse, configparser, os, subprocess, platform, json, hashlib

PIN='200f5123615808326ac796f66b02fdc6cebbcbf1'
PACKAGES=['libcamera','samurai-camera-config',
 'samurai-libssc','samurai-hexagonrpcd','samurai-radio-tools',
 'samurai-platform','samurai-gnss-assist','samurai-ssc',
 'samurai-desktop','samurai-systemd','device-realme-samurai',
 'unudhcpd','usb-signaller']
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--work',type=Path,required=True,help='New directory on Linux ext4, not NTFS')
p.add_argument('--build',action='store_true')
p.add_argument('--lax',action='store_true',help='Reuse the new chroot between package builds')
p.add_argument('--resume',action='store_true')
p.add_argument('--jobs',type=int,default=4)
a=p.parse_args()
base=a.work.resolve(); repo=Path(__file__).resolve().parents[1]
if base.exists() and not a.resume:p.error('Work directory exists; use a new path or --resume')
base.mkdir(parents=True,exist_ok=True)
tool=base/'pmbootstrap';config=base/'pmbootstrap.cfg'
env=dict(os.environ,GIT_TERMINAL_PROMPT='0',
 PMB_CHANNELS_CFG=str(repo/'channels.cfg'))
def run(args,**kwargs):
 print('+ '+' '.join(map(str,args)),flush=True)
 return subprocess.run(list(map(str,args)),check=True,env=env,**kwargs)
if not tool.exists():
 run(['git','init',tool])
 run(['git','-C',tool,'remote','add','origin','https://gitlab.postmarketos.org/postmarketOS/pmbootstrap.git'])
 # The GitHub transport mirror is declared, with the exact upstream object checked.
 run(['git','-C',tool,'remote','add','mirror','https://github.com/external-mirrors/pmbootstrap.git'])
 run(['git','-C',tool,'fetch','--depth=1','mirror',PIN])
 run(['git','-C',tool,'checkout','--detach',PIN])
assert subprocess.check_output(['git','-C',tool,'rev-parse','HEAD'],text=True).strip()==PIN
# Apply only the published functional tool delta, pinned along with upstream.
for item in json.loads((repo/'samurai/sources.json').read_text()).get('pmbootstrap_patches',[]):
 patch=repo/'samurai'/item['path']
 assert hashlib.sha256(patch.read_bytes()).hexdigest()==item['sha256']
 target=tool/item['result_path']
 if hashlib.sha256(target.read_bytes()).hexdigest()!=item['result_sha256']:
  run(['git','-C',tool,'apply','--check',patch])
  run(['git','-C',tool,'apply',patch])
 assert hashlib.sha256(target.read_bytes()).hexdigest()==item['result_sha256']
# pmbootstrap resolves channel metadata through the canonical GitLab remote.
# Initialize that metadata ref from the explicitly pinned imported commit.
base_pin=json.loads((repo/'samurai/sources.json').read_text())['pmaports_base']
if subprocess.run(['git','-C',repo,'cat-file','-e',base_pin],capture_output=True).returncode:
 run(['git','-C',repo,'fetch','--depth=1','origin',base_pin])
canonical='https://gitlab.postmarketos.org/postmarketOS/pmaports.git'
remote=subprocess.run(['git','-C',repo,'remote','get-url','upstream'],capture_output=True,text=True)
if remote.returncode:run(['git','-C',repo,'remote','add','upstream',canonical])
else:assert remote.stdout.strip()==canonical,'Unexpected upstream URL'
if subprocess.run(['git','-C',repo,'show-ref','--verify','--quiet','refs/remotes/upstream/main']).returncode:
 run(['git','-C',repo,'update-ref','refs/remotes/upstream/main',base_pin])
cfg=configparser.ConfigParser()
cfg['pmbootstrap']={'aports':str(repo),'work':str(base/'work'),'device':'realme-samurai',
 'channel':'v26.06','is_default_channel':'False',
 'kernel':'none','ui':'plasma-mobile','ui_extras':'true','service_manager':'systemd',
 'user':'user','hostname':'samurai','timezone':'Asia/Shanghai','locale':'en_US.UTF-8',
 'extra_packages':'f2fs-tools,curl,iproute2,iw,util-linux,openssh,ca-certificates,firefox-esr,discover,mobile-config-firefox',
 'extra_space':'1024','ssh_keys':'false'}
cfg['providers']={}
cfg['mirrors']={'alpine':'https://dl-cdn.alpinelinux.org/alpine/',
 'pmaports':'https://mirror.postmarketos.org/postmarketos/',
 'systemd':'https://mirror.postmarketos.org/postmarketos/extra-repos/systemd/'}
if not config.exists():
 with config.open('w') as f:cfg.write(f)
cmd=['python3',tool/'pmbootstrap.py']
if os.geteuid()==0:cmd+=['--as-root']
cmd+=['-y','-j',str(a.jobs),'-c',config]
if not (base/'initialized').exists():
 # pmbootstrap init prompts differ per pmOS release (extra packages, boot
 # size, ccache); feed a bounded run of defaults and let it finish.
 run([arg for arg in cmd if arg != '-y']+['init'],input='\n'*400,text=True)
 (base/'initialized').write_text(PIN+'\n')
run(cmd+['status'])
if a.build:
 run(cmd+['build','--arch',platform.machine(),'--lax','crossdirect'])
 build=['build','--arch','aarch64']+(['--lax'] if a.lax else [])
 run(cmd+['checksum','--verify']+PACKAGES)
 run(cmd+build+PACKAGES)
print('Configuration:',config)
print('No phone was contacted. Use install --no-image only after successful package builds.')
