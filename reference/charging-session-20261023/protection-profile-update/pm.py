"""One original traced15s PM check on the newly adopted protection cohort."""
from pathlib import Path
import argparse,importlib.util,inspect,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
adapter=load('profile_pm_adapter',HERE/'host.py');post=load('profile_pm_postboot',HERE/'postboot.py')
m=load('profile_original_pm_owner',HERE.parent/'usb-pm-notify-update/pm.py')
m.update=adapter.u;m.postboot=post;m.NAME='pm504-protection-live-20261024-01';m.REMOTE='/root/charging-management-20261023/'+m.NAME;m.GUARD=post.GUARD
# The deployment already has an independently checked current guard. Reuse
# its bytes; never replace it or the earlier fresh-validation evidence.
source=inspect.getsource(m.launch)
before="guard=Path(PACKET['guard']);assert not guard.parent.exists();guard.parent.mkdir(mode=0o700)\nsave(guard,(PACKET['boot_id']+'\\n').encode())"
after="guard=Path(PACKET['guard']);assert guard.read_bytes()==(PACKET['boot_id']+'\\n').encode()"
assert source.count(before)==1;source=source.replace(before,after)
# Correct the legacy creator label for future derivations. The executed
# first receipt remains private evidence; pm-review records that it reused
# the existing guard and does not treat that label as creation proof.
assert source.count('guard_created=True,boot_id=')==1
source=source.replace('guard_created=True,boot_id=','guard_created=False,existing_guard_revalidated=True,boot_id=')
exec(compile(source,'<current-guard-original-PM-launch>','exec'),m.__dict__)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['launch','fetch']);a=p.parse_args();print(json.dumps(getattr(m,a.action)(),indent=2))
