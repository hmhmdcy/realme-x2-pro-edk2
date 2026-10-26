"""Order the device desktop after its standard SensorProxy service."""
from pathlib import Path
import hashlib,importlib.util,json,shutil,subprocess
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel269')
spec=importlib.util.spec_from_file_location('h',R/'host.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
new='''cfgfile="/etc/greetd/samurai-phosh.toml"
# The desktop discovers SensorProxy at startup. Let the SSC service satisfy
# its own firmware/radio dependencies before exposing the desktop session.
rc_need="dbus iio-sensor-proxy ${rc_need:-}"
'''
expected=json.loads((P/'session-startup-private.json').read_text())['/etc/conf.d/greetd']
code=r'''
from pathlib import Path
import hashlib,json,os,subprocess
os.umask(0o077);out=Path('/var/lib/samurai/k269-sensor-startup-order-r1');out.mkdir(mode=0o700)
p=Path('/etc/conf.d/greetd');assert p.read_text()==EXPECTED
assert Path('/etc/init.d/iio-sensor-proxy').is_file() and Path('/etc/init.d/samurai-ssc').is_file()
levels={}
for n in ['greetd','iio-sensor-proxy','samurai-ssc','samurai-radio']:
 levels[n]=[x.parent.name for x in Path('/etc/runlevels').glob('*/'+n) if x.is_symlink()]
assert all(levels.values()),levels
(out/'greetd.confd.before').write_bytes(p.read_bytes())
try:
 p.write_text(NEW);p.chmod(0o644)
 subprocess.run(['sh','-n',str(p)],capture_output=True,check=True,timeout=5)
 q=subprocess.run(['rc-update','-u'],capture_output=True,text=True,timeout=20)
 (out/'dependency-update-private.log').write_text(q.stdout+q.stderr)
 assert q.returncode==0 and not any(x in (q.stdout+q.stderr).lower() for x in ['circular','cyclic','dependency loop'])
 report=dict(stage=269,standard_openrc_device_dependency=True,desktop_requires=['dbus','iio-sensor-proxy'],
  conflicting_desktop_before_radio_order_removed=True,config_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
  dependency_cache_update_exit=q.returncode,runlevels=levels,no_additional_service_restart=True,
  reboot_validation_pending=True,desktop_or_camera_source_modified=False)
 (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
except BaseException:
 p.write_bytes((out/'greetd.confd.before').read_bytes());subprocess.run(['rc-update','-u'],capture_output=True,timeout=20);raise
'''.replace('EXPECTED',repr(expected)).replace('NEW',repr(new))
q=h.ssh('python3 -',input=code.encode(),timeout=40);(P/'sensor-startup-order-private.json').write_bytes(q.stdout);report=json.loads(q.stdout)
(R/'sensor-startup-order-validation.json').write_text(json.dumps(report,indent=2)+'\n')
candidate=Path('/home/cy122/x2pro-linux/pmaports-camera-common269');pkg=candidate/'device/testing/samurai-desktop'
confd=pkg/'greetd.confd';assert confd.read_text()=='cfgfile="/etc/greetd/samurai-phosh.toml"\nrc_before="samurai-radio ${rc_before:-}"\n'
recipe=pkg/'APKBUILD';text=recipe.read_text();assert 'pkgrel=0\n' in text
oldhash=hashlib.sha512(confd.read_bytes()).hexdigest();confd.write_text(new);newhash=hashlib.sha512(confd.read_bytes()).hexdigest()
assert text.count(oldhash+'  greetd.confd')==1
recipe.write_text(text.replace('pkgrel=0\n','pkgrel=1\n',1).replace(oldhash+'  greetd.confd',newhash+'  greetd.confd'))
subprocess.run(['sh','-n',str(recipe)],check=True)
mirror=R.parents[1]/'linux-port/packages/samurai-desktop';assert not mirror.exists();shutil.copytree(pkg,mirror)
print(json.dumps(report,indent=2))
