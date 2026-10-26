#!/usr/bin/env python3
"""Target-only validation using the frozen #503 bindings and their $ref closure."""
import sys
sys.dont_write_bytecode = True
import hashlib, json, pathlib, shutil, subprocess, urllib.parse
from ruamel.yaml import YAML
import dtschema

OUT = pathlib.Path('/home/cy122/charging-management-20261023/dwc-flat-schema-check-01')
BINDINGS = pathlib.Path('/home/cy122/charging-management-20261023/dwc-image503-start-recovery-01/source354/Documentation/devicetree/bindings')
DTB = pathlib.Path('/mnt/e/edk2-samurai-out/charging-management-20261023/dwc-flat-board-private-01/samurai-dwc-flat-private.dtb')
DTB_SHA = '3c66a954d94ee4e9f59aac8190272dac0f247e592aac254772b043bd9cded9ae'
BINDING_SHA = 'd6f619e153675f5bc5e66f7e142d14e4f570c839ca9d23f3a9649a6a165b727b'
CORE = pathlib.Path(dtschema.__file__).parent/'schemas'
TARGET = 'usb/qcom,snps-dwc3.yaml'
PREFIX = 'http://devicetree.org/schemas/'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def save(name, obj):
    (OUT/name).write_text(json.dumps(obj, indent=2)+'\n')

def refs(item):
    if isinstance(item, dict):
        for key, val in item.items():
            if key == '$ref':
                yield val
            yield from refs(val)
    elif isinstance(item, list):
        for val in item:
            yield from refs(val)

def run(name, argv):
    with (OUT/(name+'.stdout')).open('wb') as out, (OUT/(name+'.stderr')).open('wb') as err:
        p = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=err)
        print(name, 'pid', p.pid, flush=True)
        rc = p.wait()
    save(name+'-process.json', {'argv':argv, 'pid':p.pid, 'wait_returncode':rc,
        'stdout_sha256':sha(OUT/(name+'.stdout')), 'stderr_sha256':sha(OUT/(name+'.stderr'))})
    return rc

def main():
    assert sha(DTB) == DTB_SHA and sha(BINDINGS/TARGET) == BINDING_SHA
    dest = OUT/'original-bindings'
    if dest.exists():
        raise RuntimeError('Original run exists; preserve it, do not replay')
    dest.mkdir()
    yaml = YAML(typ='safe')
    pending = [TARGET]
    pins = {}
    while pending:
        rel = pending.pop()
        if rel in pins:
            continue
        source = BINDINGS/rel
        kind = 'fixed-kernel-503'
        if not source.is_file():
            source = CORE/rel
            kind = 'dtschema-2026.9-core'
        assert source.is_file(), (rel, 'unresolved reference')
        data = yaml.load(source.read_text())
        pins[rel] = {'path':str(source), 'sha256':sha(source), 'source':kind}
        if kind == 'fixed-kernel-503':
            copy = dest/rel
            copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, copy)
        base = data['$id']
        for ref in refs(data):
            uri = urllib.parse.urljoin(base, ref).split('#')[0]
            assert uri.startswith(PREFIX), (rel, ref, uri)
            dep = uri[len(PREFIX):]
            if dep != rel:
                pending.append(dep)
    save('binding-closure.json', {'files':pins, 'target':TARGET, 'target_node':'/soc@0/usb@a600000',
        'dtb':str(DTB), 'dtb_sha256':DTB_SHA,
        'scope':'Only qcom,snps-dwc3 schema selection; referenced common schemas remain active. No all-tree pass claim.'})
    bins = OUT/'venv/bin'
    docs = sorted(str(p) for p in dest.rglob('*.yaml'))
    doc_rc = run('original-doc', [str(bins/'dt-doc-validate'), *docs])
    rc = run('original-target', [str(bins/'dt-validate'), '-s', str(dest), '-l', 'qcom,snps-dwc3',
        '--json-output', str(OUT/'original-target-diagnostics.json'), str(DTB)])
    diagnostics = json.loads((OUT/'original-target-diagnostics.json').read_text())
    save('original-result.json', {'phase':'unmodified #503 bindings', 'doc_returncode':doc_rc,
        'validate_returncode':rc, 'diagnostic_count':len(diagnostics),
        'target_schema_passed':rc==0 and not diagnostics, 'dtb_sha256_after':sha(DTB),
        'closure_unchanged':all(sha(pathlib.Path(v['path']))==v['sha256'] for v in pins.values()),
        'note':'dt-validate may exit zero even with diagnostics; pass uses diagnostic_count too.'})
    print('ORIGINAL_FINISHED', len(diagnostics), 'diagnostics', flush=True)

if __name__ == '__main__':
    main()
