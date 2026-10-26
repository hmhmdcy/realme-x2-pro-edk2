from pathlib import Path
import json,os,signal,subprocess
target=b'/mnt/e/RealmeX2Pro edk2/reference/kernel113/inspect-a11-remote-zip.py'
found=[]
for directory in Path('/proc').iterdir():
    if not directory.name.isdigit(): continue
    try: args=(directory/'cmdline').read_bytes().split(bytes([0]))
    except (FileNotFoundError,ProcessLookupError,PermissionError): continue
    if len(args)>1 and args[1]==target and Path(os.fsdecode(args[0])).name.startswith('python'):
        found.append(int(directory.name))
assert len(found)<=1, 'unexpected duplicate readers; inspect before cancelling'
children_stopped=0
for pid in found:
    children=subprocess.run(['ps','--ppid',str(pid),'-o','pid=,comm='],capture_output=True,text=True).stdout.splitlines()
    parsed=[row.split() for row in children]
    assert all(len(row)==2 and row[1]=='curl' for row in parsed)
    for child,name in parsed:
        try: os.kill(int(child),signal.SIGTERM); children_stopped+=1
        except ProcessLookupError: pass
    try: os.kill(pid,signal.SIGTERM)
    except ProcessLookupError: pass
print(json.dumps(dict(exact_readers_cancelled=len(found),curl_children_cancelled=children_stopped)))
