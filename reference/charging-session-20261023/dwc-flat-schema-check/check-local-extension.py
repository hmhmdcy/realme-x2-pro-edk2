#!/usr/bin/env python3
"""Document the existing local property, then validate the unchanged target."""
import sys
sys.dont_write_bytecode = True
import difflib, hashlib, json, pathlib, shutil, subprocess

OUT = pathlib.Path('/home/cy122/charging-management-20261023/dwc-flat-schema-check-01')
DTB = pathlib.Path('/mnt/e/edk2-samurai-out/charging-management-20261023/dwc-flat-board-private-01/samurai-dwc-flat-private.dtb')
DTB_SHA = '3c66a954d94ee4e9f59aac8190272dac0f247e592aac254772b043bd9cded9ae'
REL = 'usb/qcom,snps-dwc3.yaml'
SCHEMA_ID = 'http://devicetree.org/schemas/usb/qcom,snps-dwc3.yaml'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(name, obj):
    (OUT/name).write_text(json.dumps(obj, indent=2)+'\n')

def run(name, argv):
    with (OUT/(name+'.stdout')).open('wb') as out, (OUT/(name+'.stderr')).open('wb') as err:
        p = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=err)
        print(name, 'pid', p.pid, flush=True)
        rc = p.wait()
    save(name+'-process.json', {'argv':argv, 'pid':p.pid, 'wait_returncode':rc,
        'stdout_sha256':sha(OUT/(name+'.stdout')), 'stderr_sha256':sha(OUT/(name+'.stderr'))})
    return rc

def main():
    assert sha(DTB) == DTB_SHA
    diag = json.loads((OUT/'original-target-diagnostics.json').read_text())
    assert len(diag) == 1 and diag[0]['node'] == '/soc@0/usb@a600000'
    assert diag[0]['schema'] == SCHEMA_ID
    assert diag[0]['message'] == "Unevaluated properties are not allowed ('usb-psy-name' was unexpected)"
    closure = json.loads((OUT/'binding-closure.json').read_text())
    assert all(sha(pathlib.Path(v['path']))==v['sha256'] for v in closure['files'].values())
    dest = OUT/'local-bindings'
    if dest.exists():
        raise RuntimeError('Local run exists; preserve it, do not replay')
    shutil.copytree(OUT/'original-bindings', dest)
    original = (dest/REL).read_text()
    anchor = '  wakeup-source: true\n'
    assert original.count(anchor) == 1 and '  usb-psy-name:' not in original
    addition = ('  usb-psy-name:\n'
                '    $ref: /schemas/types.yaml#/definitions/string\n'
                '    description: |\n'
                '      Local extension naming the existing power-supply provider that\n'
                '      receives the native DWC USB input-current budget notifications.\n\n')
    changed = original.replace(anchor, addition+anchor)
    (dest/REL).write_text(changed)
    patch = ''.join(difflib.unified_diff(original.splitlines(True), changed.splitlines(True),
        fromfile='a/Documentation/devicetree/bindings/'+REL,
        tofile='b/Documentation/devicetree/bindings/'+REL))
    (OUT/'usb-psy-name-local-binding.patch').write_text(patch)
    bins = OUT/'venv/bin'
    doc_rc = run('local-doc', [str(bins/'dt-doc-validate'), *sorted(str(p) for p in dest.rglob('*.yaml'))])
    rc = run('local-target', [str(bins/'dt-validate'), '-s', str(dest), '-l', 'qcom,snps-dwc3',
        '--json-output', str(OUT/'local-target-diagnostics.json'), str(DTB)])
    diagnostics = json.loads((OUT/'local-target-diagnostics.json').read_text())
    result = {'phase':'existing usb-psy-name local extension declared',
        'doc_returncode':doc_rc, 'validate_returncode':rc, 'diagnostic_count':len(diagnostics),
        'target_schema_passed':doc_rc==0 and rc==0 and not diagnostics,
        'dtb_sha256_after':sha(DTB), 'local_binding_sha256':sha(dest/REL),
        'original_binding_sha256':sha(OUT/'original-bindings'/REL),
        'patch_sha256':sha(OUT/'usb-psy-name-local-binding.patch'),
        'fixed_sources_unchanged':all(sha(pathlib.Path(v['path']))==v['sha256'] for v in closure['files'].values()),
        'only_binding_changed':all(sha(p)==sha(dest/p.relative_to(OUT/'original-bindings'))
            for p in (OUT/'original-bindings').rglob('*.yaml') if p.relative_to(OUT/'original-bindings').as_posix()!=REL),
        'whole_tree_validated':False,
        'scope':'qcom,snps-dwc3-selected USB node plus referenced common constraints only; no DT/driver modification or hardware claim.'}
    save('local-result.json', result)
    assert result['target_schema_passed'] and result['fixed_sources_unchanged'] and result['only_binding_changed']
    print('LOCAL_TARGET_PASSED', flush=True)

if __name__ == '__main__':
    main()
