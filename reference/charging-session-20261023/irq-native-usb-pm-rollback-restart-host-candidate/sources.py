"""Pinned composition of existing owners; definitions perform no device action."""
from pathlib import Path
import hashlib, importlib.util, json, os, sys
if sys.flags.optimize: raise RuntimeError('nonoptimized Python required')
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sha = lambda raw: hashlib.sha256(raw).hexdigest()

def need(value, message):
    if not value: raise ValueError(message)

def local(value):
    value = str(value).replace('\\', '/')
    return Path('/mnt/e/' + value[3:] if os.name != 'nt' and value.startswith('E:/') else value)

def pins(): return json.loads((HERE / 'source-pins.json').read_bytes())

def source_check():
    data = pins()
    need(data['schema'] == 'samurai-irq-native-usb-pm-rollback-restart-host-sources-v1', 'source pins schema')
    for name, row in data['baseline'].items():
        raw = local(row['path']).read_bytes()
        need(sha(raw) == row['sha256'] and len(raw) == row['bytes'], 'baseline changed: ' + name)
    for name, row in data['local'].items():
        raw = (HERE / name).read_bytes()
        need(sha(raw) == row['sha256'] and len(raw) == row['bytes'], 'new source changed: ' + name)
    return data

def load(name):
    row = pins()['baseline'][name]; path = local(row['path'])
    need(sha(path.read_bytes()) == row['sha256'], 'pinned module changed: ' + name)
    spec = importlib.util.spec_from_file_location('rollback_restart_' + name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

def worker_hashes():
    return {name: pins()['local'][name]['sha256'] for name in ('eud-quiesce.py', 'eud-restart.py')}

def controller_pins():
    data = source_check()
    return {'key_transport': data['baseline']['key_transport'],
            'camera_wrapper': data['baseline']['camera_wrapper']}
