from pathlib import Path
import importlib.util,json,shlex
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel366');PRIVATE.mkdir(mode=0o700,exist_ok=True)
spec=importlib.util.spec_from_file_location('host365',Path(__file__).resolve().parents[1]/'kernel365/host.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
def raw_ssh(command,**kwargs):
    endpoint=PRIVATE/'recovered-transport-private.json'
    if not endpoint.exists():return previous.raw_ssh(command,**kwargs)
    import subprocess
    spec=importlib.util.spec_from_file_location('strict184',Path(__file__).resolve().parents[1]/'kernel184/host.py')
    base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
    selected=json.loads(endpoint.read_text());assert selected['kind']=='wifi' and selected['original_host_key_verified']
    q=subprocess.run([base.SSH,'-T',*base.OPTIONS,'-4','-o','HostKeyAlias=169.254.42.1','root@'+selected['IPAddress'],command],input=kwargs.get('input'),capture_output=True,timeout=kwargs.get('timeout',30))
    if kwargs.get('check',True) and q.returncode:raise RuntimeError('Strict original-key recovered Wi-Fi SSH failed: '+q.stderr.decode(errors='replace')[-500:])
    return q
def ssh(command,**kwargs):
    adoption=PRIVATE/'recovered-boot-adoption-private.json'
    if not adoption.exists():adoption=PRIVATE/'postboot-adoption-private.json'
    if not adoption.exists():return previous.ssh(command,**kwargs)
    guard=json.loads(adoption.read_text())['guard_path']
    raw_ssh('cmp -s /proc/sys/kernel/random/boot_id '+shlex.quote(guard),timeout=15)
    return raw_ssh(command,**kwargs)
