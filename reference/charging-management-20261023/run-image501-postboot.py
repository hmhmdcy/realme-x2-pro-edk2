"""One read-only Image501 postboot collection using the original strict key."""
from pathlib import Path
import argparse
import base64
import gzip
import importlib.util
import json
import re
import shlex

HERE = Path(__file__).resolve().parent
BASE = Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
TX = BASE / 'image501-activation/image501-gauge-live-001'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', default='postboot-r1-01-private')
    parser.add_argument('--compress', action='store_true')
    args = parser.parse_args()
    assert re.fullmatch(r'postboot-r1-[0-9]{2}-private', args.tag)
    transport = load('strict_original_key', HERE / 'eud-postboot-transport.py')
    payload = load('image501_readonly_payload', HERE / 'image501-postboot-readonly/payload.py')
    probe = json.loads((TX / 'kernel-probe-01-private/stdout-private.json').read_bytes())
    terminal = json.loads((TX / 'kernel-probe-01-private/terminal-private.json').read_bytes())
    assert terminal['returncode'] == 0 and probe['kernel_version'].startswith('#501 ')
    assert probe['flag'] == 'Y' and probe['MaxPower'] == '500' and probe['taint'] == '0'
    endpoint = json.loads(transport.ENDPOINT.read_bytes())['peer']
    request = payload.make_request(TX / 'host-context-private.json',
        BASE.parent / 'kernel481/formal-expected-private.json', endpoint, True, True)
    source = payload.make_payload(request)
    wire = source
    if args.compress:
        # Execute the exact payload and preserve its exit code; only encode stdout.
        wire = ("import base64,contextlib,gzip,io,sys\n"
                "buffer=io.StringIO();status=0\n"
                "try:\n"
                " with contextlib.redirect_stdout(buffer):\n"
                "  exec(compile(base64.b64decode(" + repr(base64.b64encode(source).decode()) +
                "),'exact-postboot-payload','exec'),{'__name__':'__main__'})\n"
                "except SystemExit as e:status=e.code\n"
                "sys.stdout.buffer.write(base64.b64encode(gzip.compress(buffer.getvalue().encode())))\n"
                "raise SystemExit(status)\n").encode()
    out = TX / args.tag
    assert not out.exists(), 'new collection directory required'
    q = transport.raw_ssh('python3 - --execute --window-confirmed --new-endpoint ' + shlex.quote(endpoint),
                          input=wire, timeout=50, check=False)
    decoded = q.stdout
    if args.compress:
        decoded = gzip.decompress(base64.b64decode(q.stdout, validate=True))
    result = payload.save_response(out, decoded, q.stderr, q.returncode, source)
    if args.compress:
        (out / 'transport-codec-private.py').write_bytes(wire)
        (out / 'transport-stdout-private.b64').write_bytes(q.stdout)
        (out / 'codec-private.json').write_text(json.dumps({'exact_payload_sha256': payload.sha(source),
            'wire_source_sha256': payload.sha(wire), 'decoded_stdout_sha256': payload.sha(decoded),
            'wire_stdout_sha256': payload.sha(q.stdout), 'returncode': q.returncode}))
    print(json.dumps(result))
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
