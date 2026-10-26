"""Build isolated camera-only daemon profiles from the installed version."""
from pathlib import Path
import json,re
R=Path(__file__).parent
P=Path('/mnt/e/edk2-samurai-out/kernel263')
d=json.loads((P/'daemon-isolation-inputs-private.json').read_text())
pw=d['files']['/usr/share/pipewire/pipewire.conf']
assert pw.count('core.name   = pipewire-0')==1
pw=pw.replace('core.name   = pipewire-0','core.name   = samurai263')
(R/'pipewire263.conf').write_text(pw)
wp=d['files']['/usr/share/wireplumber/wireplumber.conf']
wp+='''
wireplumber.profiles = {
  camera-test = {
    inherits = [ video-only, mixin.systemwide-session, mixin.stateless ]
    monitor.v4l2 = disabled
  }
}
'''
(R/'wireplumber263-off.conf').write_text(wp)
wp+='''
monitor.libcamera.rules = [
  {
    matches = [ { node.name = "~libcamera_input.*" } ]
    actions = { update-props = { node.reliable = true } }
  }
]
'''
(R/'wireplumber263-on.conf').write_text(wp)
native=(R/'native-probe.py').read_text()
native,count=re.subn(r'assert delay in \[[^\n]+\]', 'assert delay in [6000002,6000003,6000004,6000005,6000006,6000008]', native,count=1)
assert count==1
native=native.replace("args=['/usr/bin/python3','/var/lib/samurai/k263-tools/pipewire-probe.py',str(delay)]", "args=['/usr/bin/python3','/var/lib/samurai/k263-tools/isolated-runner.py',str(delay)]")
native=native.replace('time.monotonic()+(42 if delay==4000000 else 23)','time.monotonic()+40')
(R/'native-isolated.py').write_text(native)
print('Prepared off/on isolated camera profiles and a bounded cleanup harness.')
