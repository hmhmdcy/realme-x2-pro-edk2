from pathlib import Path
import importlib.util,json,types
spec=importlib.util.spec_from_file_location('camera294_transport',Path(__file__).resolve().parents[1]/'kernel294/host.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel295');PRIVATE.mkdir(mode=0o700,exist_ok=True)
spec2=importlib.util.spec_from_file_location('camera276_transport',Path(__file__).resolve().parents[1]/'kernel276/host.py')
baseline=importlib.util.module_from_spec(spec2);spec2.loader.exec_module(baseline)
fresh=types.FunctionType(baseline._fresh_raw.__code__,dict(baseline._fresh_raw.__globals__,PRIVATE=PRIVATE))
def raw_ssh(command,**kwargs):
 if (PRIVATE/'usb-ipv6-candidates-private.json').exists():return fresh(command,**kwargs)
 return previous.raw_ssh(command,**kwargs)
def ssh(command,**kwargs):
 identity=PRIVATE/'postboot-verified-private.json'
 if not identity.exists():return previous.ssh(command,**kwargs)
 expected=json.loads(identity.read_text())['boot_id']
 assert raw_ssh('cat /proc/sys/kernel/random/boot_id',timeout=15).stdout.decode().strip()==expected,'Boot changed; inspect actual state'
 return raw_ssh(command,**kwargs)
