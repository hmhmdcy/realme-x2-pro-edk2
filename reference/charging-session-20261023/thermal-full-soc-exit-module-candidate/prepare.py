"""Derive one Image502 charger ko builder; never imports or runs a device tool."""
from pathlib import Path
import ast, difflib, hashlib, json

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'charger-reattach-observation-module-candidate/build-ko.py'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
raw=BASE.read_bytes();assert sha(raw)=='de43f234d80a8f4ed494c4a228491cd6795d0b863c46a9a030b8f69b91afaf2a'
text=raw.decode()
for old,new in {
"AUTHOR = HERE.parent/'charger-reattach-observation-candidate'":"AUTHOR = HERE.parent/'thermal-full-soc-exit-candidate'",
"/charger-reattach-observation-module-01'":"/thermal-full-soc-exit-module-01'",
"/charger-reattach-observation-module-private-01'":"/thermal-full-soc-exit-module-private-01'",
"AUTHOR_DELIVERY = '6aa4d49a203258ae70f84308eb70119207e9aa1fa2ac5862ca9b88d7cf215138'":"AUTHOR_DELIVERY = '780e6591e09062da575910f1a771fd5a1605df416f79f8f9740298b844239e25'",
"samurai-mp2650-reattach-observation-private.ko":"samurai-mp2650-thermal-full-soc-exit-private.ko",
"if sys.argv[1:] == ['--check-local']:":"if sys.argv[1:] in ([], ['--check-local']):",
}.items():
    assert old in text,old;text=text.replace(old,new)
start=text.index('def source_inputs():');end=text.index('\ndef main():',start)
text=text[:start]+'''def source_inputs():
    if sys.flags.optimize: raise RuntimeError('Non-optimized Python required')
    assert sha(AUTHOR/'delivery.json') == AUTHOR_DELIVERY
    delivery = json.loads((AUTHOR/'delivery.json').read_bytes()); assert delivery['passed']
    for name, row in delivery['files'].items(): assert sha(AUTHOR/name) == row['sha256']
    test = json.loads((AUTHOR/'test-result.json').read_bytes()); assert test['passed']
    baseline = json.loads((REF/'charging-management-20261023/thermal-bands-build-result.json').read_bytes())
    assert baseline['passed'] and baseline['module_sha256'] == '10ec06fb9d798d72e08495617cfc04e7e49c77e536a12f205053e9cdbfa6297f'
    for name, digest in baseline['sources'].items(): assert sha(R8/name) == digest
    paths = {name:R8/name for name in baseline['sources']}
    for name in ['samurai-mp2650.c','mp2650-core.h','oem-full-cycle.h']:
        assert name in delivery['files']; paths[name] = AUTHOR/name
    reattach = HERE.parent/'charger-reattach-observation-candidate'
    assert sha(reattach/'delivery.json') == '6aa4d49a203258ae70f84308eb70119207e9aa1fa2ac5862ca9b88d7cf215138'
    assert sha(reattach/'reattach-observation.h') == '49cb61042d431492d91ccad917f197cbbe2fff58bc53e378aeb92c573e9666c1'
    paths['reattach-observation.h'] = reattach/'reattach-observation.h'
    includes = set(re.findall(r'^#include "([a-z0-9-]+\\.h)"', paths['samurai-mp2650.c'].read_text(), re.M))
    assert not includes-set(paths),includes-set(paths)
    return paths
''' + text[end:]
text=text.replace("    tracked.append(old_module)", """    tracked.append(old_module)
    original97c=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/charger-reattach-observation-module-private-01/samurai-mp2650-reattach-observation-private.ko')
    assert sha(original97c)=='97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd'
    tracked += [original97c,HERE.parent/'charger-reattach-observation-candidate/reattach-observation.h',
                Path('/mnt/e/edk2-samurai-out/charging-management-20261023/charger-reattach-observation-payload-private-01/forward-two-files.tar.gz'),
                Path('/mnt/e/edk2-samurai-out/charging-management-20261023/charger-reattach-observation-payload-private-01/manifest-new.json')]""")
text=text.replace("            'device_access':False", "            'old11groups91assertions_reused_not_rerun':True,'current97c_or_manifest_changed':False,\n            'device_access':False")
compile(text,str(HERE/'build-ko.py'),'exec')
(HERE/'build-ko.py').write_text(text,encoding='utf-8',newline='\n')
(HERE/'method-delta.patch').write_text(''.join(difflib.unified_diff(raw.decode().splitlines(True),text.splitlines(True),fromfile='frozen-97c-builder/build-ko.py',tofile='thermal-full-soc-exit/build-ko.py')),encoding='utf-8',newline='\n')
print(json.dumps({'builder_sha256':sha((HERE/'build-ko.py').read_bytes()),'base_builder_sha256':sha(raw)}))
