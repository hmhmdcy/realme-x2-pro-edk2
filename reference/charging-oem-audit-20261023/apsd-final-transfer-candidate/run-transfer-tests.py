from pathlib import Path
import hashlib,json,re,subprocess,tempfile
HERE=Path(__file__).resolve().parent
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def function(text,name):
    match=re.search(r'(?m)^(?:static )?(?:inline )?(?:int|void) '+name+r'\([^;]*?\)\n\{',text);assert match,name
    end=match.end();depth=1
    while depth:depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[match.start():end]+'\n'
def clean(text):return '\n'.join(line for line in text.splitlines() if not line.startswith('#include'))+'\n'
source=(HERE/'samurai-usb-input.c').read_text()
structure=re.search(r'(?ms)^struct samurai_usb_input \{.*?^\};',source).group()
original=HERE.parent/'apsd-input-backend-candidate'
prior=json.loads((original/'test-result.json').read_bytes());assert prior['passed']
inline=(original/'test-private/regmap-write-bits.actual.h').read_text()
assert sha(inline.encode())==prior['actual_regmap_inline_sha256']
assert 'NULL, false, true' in inline
fixture=(HERE/'test-transfer.c').read_text().replace('/* ACTUAL_API */',clean((HERE/'samurai-apsd-backend.h').read_text()))
fixture=fixture.replace('/* ACTUAL_DECODE */',(HERE/'samurai-usb-input-decode.h').read_text()).replace('/* ACTUAL_INLINE */',inline)
fixture=fixture.replace('/* ACTUAL_FUNCTIONS */',structure+'\n'+function(source,'samurai_usb_read_status')+(HERE/'samurai-apsd-input.inc').read_text())
# Exercise the public read wrapper too, so no actual static function is unused.
fixture=fixture.replace('reset();map.command=0xa5;', 'reset();struct samurai_apsd_bus_sample observed;input.apsd_sample_serial=0;assert(!samurai_usb_apsd_read(&input,&observed)&&observed.serial==1);map.reads=0;map.command=0xa5;')
flags=['-std=gnu11','-g','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie']
with tempfile.TemporaryDirectory(prefix='samurai-final-transfer-') as directory:
    root=Path(directory);code=root/'actual.c';code.write_text(fixture);binary=root/'test'
    built=subprocess.run(['gcc',*flags,str(code),'-o',str(binary)],capture_output=True,text=True)
    assert built.returncode==0,built.stderr
    child=subprocess.run([str(binary)],capture_output=True,text=True,timeout=30)
    assert child.returncode==0,(child.returncode,child.stdout,child.stderr)
    groups=child.stdout.splitlines();assert len(groups)==9 and not child.stderr
result=dict(passed=True,groups=groups,group_count=len(groups),flags=flags,actual_backend_and_reader=True,
    actual_kernel_forced_regmap_inline=True,hardware_registration_and_owner_validation_modeled=True,
    fixture_sha256=sha(fixture.encode()),phone_accessed=False,
    files={name:sha((HERE/name).read_bytes()) for name in ['samurai-apsd-backend.h','samurai-apsd-input.inc','samurai-usb-input.c','samurai-usb-input-decode.h','test-transfer.c','run-transfer-tests.py']})
with (HERE/'transfer-test-result.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(dict(passed=True,groups=len(groups))))
