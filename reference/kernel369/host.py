from pathlib import Path
import importlib.util,json,shlex,subprocess
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel369');PRIVATE.mkdir(mode=0o700,exist_ok=True)
spec=importlib.util.spec_from_file_location('host367',Path(__file__).resolve().parents[1]/'kernel367/host.py')
previous=importlib.util.module_from_spec(spec);spec.loader.exec_module(previous)
def raw_ssh(command,**kwargs):
 endpoint=PRIVATE/'current-transport-private.json'
 if not endpoint.exists():return previous.raw_ssh(command,**kwargs)
 spec=importlib.util.spec_from_file_location('strict184',Path(__file__).resolve().parents[1]/'kernel184/host.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
 selected=json.loads(endpoint.read_text());assert selected['kind']=='wifi' and selected['original_key_verified']
 q=subprocess.run([base.SSH,'-T',*base.OPTIONS,'-4','-o','HostKeyAlias=169.254.42.1','root@'+selected['IPAddress'],command],input=kwargs.get('input'),capture_output=True,timeout=kwargs.get('timeout',30))
 if kwargs.get('check',True) and q.returncode:raise RuntimeError('Strict recovered Wi-Fi SSH failed: '+q.stderr.decode(errors='replace')[-400:])
 return q
def ssh(command,**kwargs):
 guard_file=PRIVATE/'recovered-boot-adoption-private.json'
 if not guard_file.exists():guard_file=PRIVATE.parent/'kernel367/postboot-adoption-private.json'
 guard=json.loads(guard_file.read_text())['guard_path'];raw_ssh('cmp -s /proc/sys/kernel/random/boot_id '+shlex.quote(guard),timeout=15)
 return raw_ssh(command,**kwargs)
