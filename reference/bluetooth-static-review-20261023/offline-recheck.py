"""Recheck selected static defects without importing Bluetooth/WinRT/SSH code."""
from pathlib import Path,PureWindowsPath
from types import SimpleNamespace
import ast,hashlib,json,re,subprocess

ROOT=Path(__file__).resolve().parents[2]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
phone=ROOT/'reference/bluetooth-le-peer-20261023/phone-gatt-peer.py'
tree=ast.parse(phone.read_text())
peer=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='PeerRun')
stop=next(n for n in peer.body if isinstance(n,ast.FunctionDef) and n.name=='stop')
namespace={}
exec(compile(ast.fix_missing_locations(ast.Module(body=[stop],type_ignores=[])),str(phone),'exec'),namespace)
events=[]
def failed_log(*args,**kwargs):
    events.append('log_attempt')
    raise OSError('injected offline log write failure')
fake=SimpleNamespace(stopping=False,accepting=True,note=failed_log)
try:namespace['stop'](fake,'offline-test')
except OSError:pass
else:raise AssertionError('Actual stop method unexpectedly swallowed log failure')
assert fake.stopping and not fake.accepting
assert namespace['stop'](fake,'second-stop') is False and events==['log_attempt']

orchestrator=ROOT/'reference/bluetooth-20261023/run-gatt-window.py'
central=ROOT/'reference/bluetooth-windows-central-20261023/windows-gatt-central.cs'
text=central.read_text()
windows_root=PureWindowsPath(re.search(r'PrivateRoot = @"([^"]+)"',text).group(1))
sample=Path('/mnt/e/edk2-samurai-out/bluetooth-20261023/gatt-r3')
assert Path('/mnt/e/edk2-samurai-out') in sample.parents
mapped=PureWindowsPath('E:/edk2-samurai-out/bluetooth-20261023/gatt-r3/windows-result-private.json')
assert not mapped.is_relative_to(windows_root)

# This minimal shell case verifies errexit's OR-list semantics only. It performs
# no production helper, DMS, filesystem redirection or radio operation.
shell=subprocess.run(['dash','-ec','refresh() { printf before; false; printf after; }; load() { refresh || return "$?"; }; load'],capture_output=True,timeout=3)
assert shell.returncode==0 and shell.stdout==b'beforeafter'
print(json.dumps(dict(actual_stop_method_log_failure_skips_second_cleanup=True,
    output_containment_clause_accepts_path_that_central_rejects=True,full_orchestrator_preflight_run=False,
    shell_or_list_disables_errexit_in_called_function=True,
    source_sha256={str(p.relative_to(ROOT)):digest(p) for p in [phone,orchestrator,central]},
    production_source_changed=False,phone_radio_ssh_winrt_or_driver_access=False),indent=2))
