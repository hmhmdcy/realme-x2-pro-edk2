"""Read only the actual completed IRQ adoption; never create a runtime identity."""
from pathlib import Path
import hashlib, importlib.util, json, re, sys
if sys.flags.optimize: raise RuntimeError('optimized interpreter is unsupported')
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
BASE = Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
MANIFEST = '5fca8e5a0795325bd780b7965579068c7edc35fa7da12bac357bb30bbde69417'
BOOT = 'eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06'
LOGDUMP = 'ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1'
KEY_SHA = '7f49a922e0babf167c77ad6e9bd7edf63e437418d5134e3d081fb8a0082a4f4c'
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def need(value, message):
    if not value: raise ValueError(message)


def local(value):
    text = str(value).replace('\\', '/')
    if sys.platform != 'win32' and re.match(r'^[A-Za-z]:/', text):
        text = '/mnt/' + text[0].lower() + text[2:]
    return Path(text).resolve()


def adoption_module():
    pins = json.loads((HERE / 'source-pins.json').read_bytes())
    for name, row in pins.items():
        need(sha((REF / row['path']).read_bytes()) == row['sha256'], 'source changed: ' + name)
    spec = importlib.util.spec_from_file_location('icon_irq_adoption_profile', REF / pins['irq_profile']['path'])
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module.adoption_module()


def review_adoption(context_path, camera_path, probe_directory, capture_directory):
    """Return source-authenticated facts only after postboot AND adoption receipts."""
    context, camera, probe, capture = map(local, (context_path, camera_path, probe_directory, capture_directory))
    module = adoption_module()
    adoption, raw_sources = module.review(context, camera, probe, capture)
    tx, boot, guard = adoption['transaction_id'], adoption['boot'], adoption['guard']
    need(re.fullmatch(r'usb-irq-protection-activate-[a-z0-9-]{8,48}', tx)
         and context.parent.name == tx and boot != adoption['old_boot'], 'real IRQ activation/new boot required')
    need(guard == '/var/lib/samurai/' + tx + '-adopted/boot-id-private.txt'
         and adoption['manifest'] == MANIFEST and adoption['candidate_boot_sha256'] == BOOT
         and adoption['candidate_logdump_sha256'] == LOGDUMP, 'IRQ adopted profile differs')
    folder = context.parent / 'irq-adoption-01-private'
    paths = {'context': context, 'camera': camera, 'postboot': capture / 'stdout-private.json',
             'adopt_request': folder / 'adopt-request-private.json',
             'executed': folder / 'executed-adoption-source.py',
             'dispatch': folder / 'dispatch-intent-private.json',
             'child': folder / 'adopt-child-private.json', 'terminal': folder / 'adopt-terminal-private.json',
             'reply': folder / 'adopt-stdout-private.json', 'stderr': folder / 'adopt-stderr-private.txt',
             'result': folder / 'adoption-result-private.json',
             'old_pointer': folder / 'boot-adoption-before-irq-private.json',
             'pointer': folder / 'adoption-pointer-private.json', 'endpoint': folder / 'new-endpoint-private.json',
             'current_pointer': BASE / 'boot-adoption-private.json', 'key_transport': REF / 'kernel184/host.py'}
    values = {name: path.read_bytes() for name, path in paths.items()}
    parsed = {name: json.loads(value) for name, value in values.items()
              if name not in ('executed', 'stderr', 'key_transport')}
    need(parsed['adopt_request'] == adoption and values['executed'] == module.payload(adoption, raw_sources),
         'actual adoption request/executed source differs')
    module.check_previous(parsed['old_pointer'], adoption)
    argv = module.host_module().transport_argv(adoption['endpoint'])
    dispatch, child, terminal = (parsed[name] for name in ('dispatch', 'child', 'terminal'))
    code_sha = sha(values['executed'])
    need(type(dispatch.get('request_count')) is int
         and dispatch == {'request_count': 1, 'argv': argv, 'stdin_sha256': code_sha, 'no_replay': True},
         'sole original adoption dispatch required')
    need(type(child.get('pid')) is int and child['pid'] > 0 and type(child.get('start_ticks')) is int
         and child['start_ticks'] > 0 and isinstance(child.get('observed_argv'), list)
         and child['observed_argv'] and all(isinstance(value, str) and value for value in child['observed_argv'])
         and child.get('argv') == argv
         and child.get('stdin_sha256') == code_sha, 'actual adoption child identity/input missing')
    need(all(terminal.get(key) == child[key] for key in ('pid', 'start_ticks', 'argv', 'observed_argv', 'stdin_sha256'))
         and terminal.get('terminal') is True and type(terminal.get('returncode')) is int
         and terminal['returncode'] == 0 and terminal.get('primary_error') is None
         and terminal.get('cleanup_errors') == []
         and terminal.get('stdout_sha256') == sha(values['reply'])
         and terminal.get('stderr_sha256') == sha(values['stderr']), 'actual adoption did not finish cleanly')
    reply = parsed['reply']
    fixed = {'guard_created': True, 'old_guards_preserved': True, 'transaction_id': tx, 'boot_id': boot,
             'guard': guard, 'postboot_raw_sha256': adoption['postboot_raw_sha256'],
             'fresh_validation_passed': True, 'cohort_verified': True,
             'charging_controls_written': False, 'hardware_writes': 0}
    need(all(reply.get(key) == value for key, value in fixed.items())
         and reply.get('guard_sha256') == sha((boot + '\n').encode())
         and re.fullmatch(r'[0-9a-f]{64}', reply.get('fresh_validation_sha256', '')), 'fresh adoption reply differs')
    pointer = {'guard_path': guard, 'original_key_verified': True, 'baseline481_verified': True,
               'Image502_verified': True, 'USB_IRQ_protection_verified': True, 'charging_manifest_sha256': MANIFEST,
               'candidate_boot_sha256': BOOT, 'candidate_logdump_sha256': LOGDUMP,
               'postboot_raw_sha256': adoption['postboot_raw_sha256'],
               'fresh_validation_sha256': reply['fresh_validation_sha256'],
               'stage_transaction_id': adoption['stage_transaction_id']}
    endpoint = {'kind': 'usb-ipv6', 'peer': adoption['endpoint'], 'interface_index': 29,
                'host_key_alias': '169.254.42.1', 'original_key_verified': True, 'observed_new_boot': boot,
                'guard_path': guard, 'postboot_Image502_passed': True, 'postboot_USB_IRQ_protection_passed': True}
    need(parsed['pointer'] == parsed['current_pointer'] == pointer and parsed['endpoint'] == endpoint,
         'current pointer/endpoint is not this actual IRQ adoption')
    need(parsed['result'] == {'passed': True, 'pointer': pointer, 'old_pointer_and_guards_preserved': True,
         'no_charge_or_USB_or_carrier_control_write': True}, 'actual adoption result differs')
    need(sha(values['key_transport']) == KEY_SHA, 'original strict key source changed')
    raw = parsed['postboot']['raw']
    notes = {}
    for group in ('charging_modules', 'camera_modules'):
        for name, row in raw[group].items():
            name = name.replace('-', '_'); note = row['loaded_note_sha256']
            need(re.fullmatch(r'[0-9a-f]{64}', note) and (name not in notes or notes[name] == note), 'invalid actual note')
            notes[name] = note
    need('s5k3m5' not in notes and re.fullmatch(r'[0-9a-f]{64}', raw['sensor_note']), 'invalid sensor note')
    notes['s5k3m5'] = raw['sensor_note']
    return {'adoption': adoption, 'boot_id': boot, 'guard_path': guard, 'guard_sha256': reply['guard_sha256'],
            'runtime_expected': {**{key: adoption[key] for key in ('release', 'version', 'rootfs')}, 'notes': notes},
            'pointer': pointer, 'endpoint': endpoint,
            'review_inputs': dict(zip(('context', 'camera', 'probe_directory', 'capture_directory'),
                                     map(str, (context, camera, probe, capture)))),
            'files': {name: {'path': str(path), 'sha256': sha(values[name])} for name, path in paths.items()}}
