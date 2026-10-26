"""Own one PM worker and keep its actual terminal even if SSH disconnects."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
sys.dont_write_bytecode=True
def save(path,value):
    with path.open('x') as file:json.dump(value,file,indent=2);file.write('\n');file.flush();os.fsync(file.fileno())
def observed(pid):
    directory=Path('/proc',str(pid));fields=(directory/'stat').read_text().rsplit(')',1)[1].split()
    return dict(pid=pid,startticks=int(fields[19]),argv=[part.decode() for part in (directory/'cmdline').read_bytes().split(b'\0') if part])
def supervise(directory):
    directory=Path(directory).resolve();worker=directory/'worker.py'
    intent=json.loads((directory/'launch-private.json').read_bytes())
    assert hashlib.sha256(worker.read_bytes()).hexdigest()==intent['worker_sha256']
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==intent['boot_id']
    save(directory/'supervisor-process-private.json',observed(os.getpid()))
    with (directory/'worker-stdout-private.txt').open('xb') as out,(directory/'worker-stderr-private.txt').open('xb') as err:
        child=subprocess.Popen([sys.executable,'-B',str(worker)],stdin=subprocess.DEVNULL,stdout=out,stderr=err,close_fds=True)
        primary=None;receipt=None;terminal=False
        try:receipt=observed(child.pid);save(directory/'worker-process-private.json',receipt)
        except BaseException as error:primary=repr(error)
        finally:
            child.wait();terminal=True
            out.flush();err.flush();os.fsync(out.fileno());os.fsync(err.fileno())
            save(directory/'worker-terminal-private.json',dict(pid=child.pid,process=receipt,terminal=terminal,returncode=child.returncode,receipt_error=primary))
    return child.returncode
if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--supervise':raise SystemExit(supervise(sys.argv[2]))
    print(json.dumps(dict(source_only=True,device_accessed=False)))
