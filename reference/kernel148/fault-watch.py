"""Capture fresh device coredumps during a bounded driver debugging window."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys,time
p=argparse.ArgumentParser();p.add_argument('label');p.add_argument('--seconds',type=int,default=1800);p.add_argument('--worker',action='store_true');a=p.parse_args()
assert a.label.replace('-','').isalnum() and 30<=a.seconds<=3600
os.umask(0o077);out=Path('/var/lib/samurai')/('k148-'+a.label)
if not a.worker:
    out.mkdir(mode=0o700)
    (out/'boot-id-private.txt').write_bytes(Path('/proc/sys/kernel/random/boot_id').read_bytes())
    assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
    with (out/'watch-private.log').open('wb') as log:
        child=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),a.label,'--seconds',str(a.seconds),'--worker'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    (out/'watch-pid-private.txt').write_text(str(child.pid)+'\n')
    for _ in range(20):
        if (out/'status.json').exists():break
        if child.poll() is not None:raise RuntimeError('Fault watcher failed to start')
        time.sleep(.1)
    assert (out/'status.json').exists()
    print(json.dumps(dict(watcher_started=True,duration_seconds=a.seconds)))
    raise SystemExit(0)

boot=(out/'boot-id-private.txt').read_bytes();start=time.monotonic();saved=set();errors=[]
baseline=subprocess.check_output(['dmesg'],text=True).count('gpu fault:')
def snapshot(cmd,name):
    with (out/name).open('wb') as log:
        subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=30)
def status(active):
    row=dict(active=active,elapsed_seconds=time.monotonic()-start,cores_saved=len(saved),capture_errors=len(errors),boot_preserved=Path('/proc/sys/kernel/random/boot_id').read_bytes()==boot,taint=Path('/proc/sys/kernel/tainted').read_text().strip())
    temporary=out/'status.tmp';temporary.write_text(json.dumps(row,indent=2)+'\n');temporary.replace(out/'status.json')
status(True)
while time.monotonic()-start<a.seconds and Path('/proc/sys/kernel/random/boot_id').read_bytes()==boot:
    for dev in Path('/sys/class/devcoredump').glob('devcd*'):
        if dev.name in saved:continue
        try:
            snapshot(['cat',str(dev/'data')],dev.name+'-private.data')
            saved.add(dev.name)
            snapshot(['dmesg'],dev.name+'-dmesg-private.txt')
            gem=Path('/sys/kernel/debug/dri/1/gem')
            if gem.is_file():snapshot(['cat',str(gem)],dev.name+'-gem-private.txt')
        except (OSError,subprocess.SubprocessError) as e:
            errors.append(dict(device=dev.name,type=type(e).__name__))
            (out/'capture-errors-private.json').write_text(json.dumps(errors,indent=2)+'\n')
    status(True);time.sleep(1)
status(False)
final=subprocess.check_output(['dmesg'],text=True).count('gpu fault:')
(out/'fault-counts.json').write_text(json.dumps(dict(before=baseline,after=final),indent=2)+'\n')
(out/'SHA256SUMS').write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  ./'+f.name+'\n' for f in sorted(out.iterdir()) if f.is_file() and f.name!='SHA256SUMS'))
