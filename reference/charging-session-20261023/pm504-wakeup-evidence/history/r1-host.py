"""One new scoped wakeup-evidence transaction; original PM owner retained."""
from pathlib import Path
import hashlib,importlib.util,inspect,sys
sys.dont_write_bytecode=True
if sys.flags.optimize:raise RuntimeError('nonoptimized Python required')
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'irq-native-usb-pm-postboot-host-candidate'
sys.path.insert(0,str(OLD))
s=importlib.util.spec_from_file_location('pm504_original_smoke_builder',OLD/'pm-smoke-host.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

def worker_code(request):
    device=(m.host.DEVICE/'device.py').read_bytes().split(b"\nif __name__=='__main__':",1)
    original=(OLD/'pm-smoke-worker.inc').read_bytes()
    body,tail=original.rsplit(b"\nif __name__=='__main__':",1)
    m.host.need(body.count(b'def pm_smoke():')==1,'exact original worker body')
    body=body.replace(b'def pm_smoke():',b'def pm_smoke_base():',1)
    return (('PM_REQUEST='+repr(request)+'\n').encode()+device[0]+b'\n'+m.inputs()+b'\n'+body+
            b'\n'+(HERE/'trace-worker.inc').read_bytes()+b"\nif __name__=='__main__':"+tail)

m.worker_code=worker_code
source=inspect.getsource(m.launch)
assert source.count('pm504-smoke-live-20261024-01')==2 and source.count('pm-smoke-01-private')==1
source=source.replace('pm504-smoke-live-20261024-01','pm504-wakeup-live-20261024-02').replace('pm-smoke-01-private','pm-wakeup-02-private')
source=source.replace('one supervised PM transaction; no driver, charge-policy, service or partition writes',
                      'one supervised PM transaction and private scoped wakeup trace; no charge-policy, wakeup-policy, driver, service or partition writes')
exec(compile(source,'<original-pm-owner-new-evidence-namespace>','exec'),m.__dict__)

if __name__=='__main__':m.main()
