"""Fixed -C composition of frozen IRQ postboot/adoption; import is inert."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import sys
from types import SimpleNamespace

if sys.flags.optimize:
    raise RuntimeError('optimized Python disables reviewed checks')
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BASE = HERE.parent
HOST = BASE / 'irq-cohort-postboot-host-candidate'
ADOPT = BASE / 'irq-cohort-adoption-candidate'
SOURCE_PINS = {
    'host.py': (HOST / 'host.py', '58d0cbf0dd4ec2db29725bdfd2b01467cbe04c4401b1ca411960438e66dca6e7'),
    'host-delivery': (HOST / 'delivery.json', '8a4301cb9850dcab65069f6ec0e2ca47b8be72b1fcbb2676357863518f640d2a'),
    'adopt.py': (ADOPT / 'adopt.py', '6f0a0da1da20b3013d27c20b97d817c9db1bfc00b3e1d3ee2db59411a04c5b44'),
    'adopt-delivery': (ADOPT / 'delivery.json', 'd5946973156dd800d1028ccb740828c87cd82c763ec6c48064f35c036bd40e14'),
}
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def need(value, message):
    if not value:
        raise ValueError(message)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_sources():
    for name, (path, digest) in SOURCE_PINS.items():
        need(sha(path.read_bytes()) == digest, 'frozen original changed: ' + name)
    # These original checks authenticate their complete transitive inputs.
    original = load(ADOPT / 'adopt.py', 'compressed_irq_original_source_check')
    original.sources()
    original.host_module().source_check()
    return {name: digest for name, (_, digest) in SOURCE_PINS.items()}


def host_module():
    check_sources()
    module = load(HOST / 'host.py', 'compressed_irq_frozen_host')
    original = module.transport_argv

    def compressed_argv(endpoint, *, collection=False):
        argv = original(endpoint, collection=collection)
        need(argv[:3] == ['/mnt/c/Windows/System32/OpenSSH/ssh.exe', '-6', '-T']
             and '-C' not in argv, 'unexpected original strict transport')
        return [argv[0], '-C', *argv[1:]]

    # saved_transport and every other original body keep using this module's
    # globals, so sent argv and authenticated saved argv have one fixed profile.
    module.transport_argv = compressed_argv
    return module


def adoption_module():
    check_sources()
    module = load(ADOPT / 'adopt.py', 'compressed_irq_frozen_adoption')
    module.host_module = host_module
    return module


def aliases(out, adoption):
    """Retain exact original transport bytes under the postboot contract names."""
    for source, target in [
            ('adopt-stdout-private.json', 'stdout-private.json'),
            ('adopt-stderr-private.txt', 'stderr-private.txt'),
            ('adopt-child-private.json', 'child-private.json'),
            ('adopt-terminal-private.json', 'terminal-private.json')]:
        path = out / source
        if path.exists():
            adoption.create(out / target, path.read_bytes())


def send_readonly(out, code, *, collection=False):
    """Original owned Popen/EOF/finally-wait, with exact-byte receipt aliases."""
    host, adoption = host_module(), adoption_module()
    host_for_transfer = SimpleNamespace(transport_argv=lambda endpoint:
        host.transport_argv(endpoint, collection=collection))
    adoption.create(out / 'executed-device-source.py', code)
    adoption.save(out / 'compression-profile-private.json', {
        'profile_sha256': sha(Path(__file__).read_bytes()),
        'original_sources': check_sources(), 'compression': '-C',
        'original_owned_transfer_reused': True, 'collection': collection,
    })
    try:
        return adoption.transfer(out, code, host_for_transfer, host.PEER)
    finally:
        # Failed or malformed responses still retain their actual raw bytes.
        # An absent original receipt remains absent, never synthesized.
        aliases(out, adoption)


def output_path(context, out):
    context, out = Path(context).resolve(), Path(out).resolve()
    need(out.is_relative_to(context.parent) and out != context.parent
         and not out.exists(), 'new output within the actual activation is required')
    return out


def probe(context, out):
    host = host_module()
    code = host.probe_payload(context, host.PEER)  # Authenticate before mkdir.
    out = output_path(context, out)
    out.mkdir(mode=0o700)
    send_readonly(out, code)
    return host.review_probe(context, out)


def collect(context, camera, probe_directory, out):
    host = host_module()
    out = output_path(context, out)
    host.bind(out, context, camera, probe_directory)
    request = host.make_request(context, camera, probe_directory)
    code = host.make_payload(request)
    need((out / 'device-payload-private.py').read_bytes() == code,
         'bound original payload changed')
    send_readonly(out, code, collection=True)
    return host.evaluate_response(context, camera, probe_directory, out)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', nargs='?', default='check-local',
                        choices=['check-local', 'probe', 'collect', 'adopt'])
    for name in ['context', 'camera', 'probe-directory', 'capture-directory', 'output']:
        parser.add_argument('--' + name)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--window-confirmed', action='store_true')
    args = parser.parse_args(argv)
    if args.action == 'check-local':
        check_sources()
        print(json.dumps({'source_checked': True, 'device_accessed': False,
                          'runtime_request_generated': False, 'compression': '-C'}))
        return
    need(args.execute and args.window_confirmed, 'explicit action and current owner window required')
    os.umask(0o077)
    if args.action == 'probe':
        result = probe(args.context, args.output)
    elif args.action == 'collect':
        result = collect(args.context, args.camera, args.probe_directory, args.output)
    else:
        result = adoption_module().adopt(args.context, args.camera, args.probe_directory,
                                         args.capture_directory, True)
    # Full identities and endpoint fields belong in the private output files.
    print(json.dumps({'action': args.action, 'completed': True,
                      'passed': result.get('passed', result.get('adopted')),
                      'physical_delivery_or_latency_accepted': False}))


if __name__ == '__main__':
    main()
