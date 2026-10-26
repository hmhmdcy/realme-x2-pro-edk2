from pathlib import Path
import importlib.util,json,subprocess
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel360')
PRIVATE.mkdir(mode=0o700,exist_ok=True)
def raw_ssh(command,**kwargs):
    spec=importlib.util.spec_from_file_location('strict184',Path(__file__).resolve().parents[1]/'kernel184/host.py')
    base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
    q=subprocess.run([base.SSH,'-T',*base.OPTIONS,'root@169.254.42.1',command],input=kwargs.get('input'),capture_output=True,timeout=kwargs.get('timeout',30))
    if kwargs.get('check',True) and q.returncode:raise RuntimeError('Strict original-key USB SSH failed: '+q.stderr.decode(errors='replace')[-500:])
    return q
def ssh(command,**kwargs):
    adopted=json.loads((PRIVATE/'recovered-boot-adoption-private.json').read_text())
    raw_ssh('cmp -s /proc/sys/kernel/random/boot_id '+adopted['guard_path'],timeout=15)
    return raw_ssh(command,**kwargs)
