"""Render an inspection script by default; --live requires a fresh handoff."""
from pathlib import Path
import argparse
import ast
import hashlib
import json
import shlex
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
PRIVATE=Path("/mnt/e/edk2-samurai-out/kernel451")

REMOTE=r'''from pathlib import Path
import hashlib,json,os,runpy,time,traceback
root=Path(ROOT)
expected=EXPECTED
assert expected!='FRESH_HANDOFF_REQUIRED'
assert hashlib.sha256((root/'handoff-private.json').read_bytes()).hexdigest()==expected
handoff=json.loads((root/'handoff-private.json').read_text())
assert handoff['schema']=='samurai-camera-handoff-v1' and handoff['window_owner']=='camera'
assert handoff['fresh_preflight_verified'] and handoff['window_id']==root.name
assert Path(handoff['boot_guard_path']).read_bytes()==Path('/proc/sys/kernel/random/boot_id').read_bytes()
state=json.loads((root/'state.json').read_text())
userroot=Path('/run/user/10000')/('k450-user-'+root.name)
def residual():
 found=[]
 for entry in Path('/proc').glob('[0-9]*'):
  try:
   fields=(entry/'stat').read_text().rsplit(')',1)[1].split()
   if fields[0]=='Z':continue
   args=[part.decode() for part in (entry/'cmdline').read_bytes().split(bytes([0])) if part]
   exe=os.readlink(entry/'exe')
   owned=exe.startswith(str(userroot)+'/') or any(arg in [
     str(root/'worker.py'),str(root/'pipeline-fixture'),str(userroot)
   ] for arg in args)
   if owned:found.append(int(entry.name))
  except (OSError,UnicodeDecodeError):pass
 return found
result=dict(window_id=root.name,phase=state['phase'],terminal=state['terminal'],
            handoff_sha256=expected,passed=False,worker_exited=False)
if state['terminal']:
 deadline=time.monotonic()+2
 remaining=residual()
 while remaining and time.monotonic()<deadline:
  time.sleep(.05);remaining=residual()
 result.update(worker_exited=int(state['pid']) not in remaining,
               residual_processes=remaining,user_directory_exists=userroot.exists(),
               transaction_passed=state['passed'])
 if state['passed'] and not remaining and not userroot.exists():
  try:
   functions=runpy.run_path(str(root/'capture-body-comparison.py'))
   result['current_final_checks']=functions['finalize'](root,state)
   result['passed']=bool(result['worker_exited'] and result['current_final_checks']['passed'])
  except BaseException:
   result['current_final_check_failure']=traceback.format_exc()
else:
 result['completed_segments']=list(state.get('sustained',{}))
print(json.dumps(result))
'''

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--attempt",default="r1")
    parser.add_argument("--handoff",type=Path)
    parser.add_argument("--live",action="store_true")
    args=parser.parse_args()
    assert args.attempt.startswith("r") and args.attempt[1:].isdigit()
    window="k451-proxy-comparison-"+args.attempt
    digest="FRESH_HANDOFF_REQUIRED"
    if args.handoff:
        handoff=json.loads(args.handoff.read_text())
        assert handoff["window_id"]==window and handoff["window_owner"]=="camera"
        assert handoff["fresh_preflight_verified"] is True
        digest=hashlib.sha256(args.handoff.read_bytes()).hexdigest()
    source=REMOTE.replace("ROOT",repr("/var/lib/samurai/"+window)).replace("EXPECTED",repr(digest))
    ast.parse(source)
    PRIVATE.mkdir(mode=0o700,exist_ok=True)
    (PRIVATE/f"comparison-inspect-{args.attempt}.py").write_text(source)
    if not args.live:
        print(json.dumps(dict(stage=451,rendered=True,phone_accessed=False,
                              live_requires_explicit_flag_and_fresh_handoff=True,passed=True)))
        return
    assert args.handoff and digest!="FRESH_HANDOFF_REQUIRED"
    import host
    # The remote script checks the newly supplied guard and handoff bytes.
    # Avoid inheriting host.ssh's historical boot-guard/charging assumptions.
    result=host.raw_ssh("python3 -c "+shlex.quote(source),timeout=25)
    result.check_returncode()
    data=json.loads(result.stdout)
    index=1
    while (PRIVATE/f"comparison-live-{args.attempt}-{index}-private.json").exists():
        index+=1
    (PRIVATE/f"comparison-live-{args.attempt}-{index}-private.json").write_bytes(result.stdout)
    print(json.dumps(data,indent=2))

if __name__=="__main__":
    main()
