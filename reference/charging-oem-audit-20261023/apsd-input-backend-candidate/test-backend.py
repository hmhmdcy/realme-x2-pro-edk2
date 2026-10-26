"""Only new transport + actual R7 status/budget/stop/resume boundaries."""
from pathlib import Path
import hashlib,json,re,subprocess
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pins={'samurai-usb-input.c':'fc7c42cf6f0df20a522c0d41e8d78d6c50d38dc85ab00f35e3583edf3c4427d7',
      'samurai-apsd-input.inc':'ef6baeeeb927f7e74159ba1f8b339a55f2c7ee3d8f050ebad3d17ee0689f4ff2',
      'samurai-apsd-backend.h':'00d5659e8028a18be6f9db990cb9221af8475cf434693e3b995612f04f6cee94'}
assert all(sha(HERE/n)==h for n,h in pins.items())
def function(text,name):
 m=re.search(r'(?m)^(?:static )?(?:inline )?(?:int|void) '+name+r'\([^;]*?\)\n\{',text)
 assert m,name
 end=m.end();level=1
 while level:level+=(text[end]=='{')-(text[end]=='}');end+=1
 return text[m.start():end]+'\n'
def clean(text):return '\n'.join(x for x in text.splitlines() if not x.startswith('#include'))+'\n'
source=(HERE/'samurai-usb-input.c').read_text()
baseline=(REF/'charging-session-20261023/r8-source-integration/kernel-sources/drivers/power/supply/samurai-usb-input.c').read_text()
functions={n:function(source,n) for n in ['samurai_usb_read_status','samurai_usb_get_budget','samurai_usb_stop','samurai_usb_suspend','samurai_usb_resume']}
assert all(functions[n]==function(baseline,n) for n in ['samurai_usb_read_status','samurai_usb_get_budget'])
regmap=Path('/mnt/samurai-full282/source354/include/linux/regmap.h')
regmap_func=function(regmap.read_text(),'regmap_write_bits')
assert 'regmap_update_bits_base(map, reg, mask, val, NULL, false, true)' in regmap_func
struct=re.search(r'(?ms)^struct samurai_usb_input \{.*?^\};',source).group(0)
body='\n'.join([struct,functions['samurai_usb_read_status'],(HERE/'samurai-apsd-input.inc').read_text(),
                functions['samurai_usb_get_budget'],functions['samurai_usb_stop'],functions['samurai_usb_suspend'],functions['samurai_usb_resume']])
fixture=(HERE/'test-fixture.c').read_text().replace('/* ACTUAL_API */',clean((HERE/'samurai-apsd-backend.h').read_text()))
fixture=fixture.replace('/* ACTUAL_DECODE */',(HERE/'samurai-usb-input-decode.h').read_text()).replace('/* ACTUAL_REGMAP_INLINE */',regmap_func).replace('/* ACTUAL_FUNCTIONS */',body)
out=HERE/'test-private';out.mkdir(exist_ok=True)
(out/'actual-backend.c').write_text(fixture)
(out/'regmap-write-bits.actual.h').write_text(regmap_func)
cmd=['gcc','-std=gnu11','-g','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(out/'actual-backend.c'),'-o',str(out/'test-backend')]
q=subprocess.run(cmd,capture_output=True,text=True);(out/'compile.txt').write_text(q.stdout+q.stderr)
if q.returncode:print(q.stderr);raise SystemExit(q.returncode)
q=subprocess.run([str(out/'test-backend')],capture_output=True,text=True)
(out/'run.txt').write_text(q.stdout+q.stderr);print(q.stdout+q.stderr)
assert all(sha(HERE/n)==h for n,h in pins.items()),'Author sources changed while testing'
result={'passed':q.returncode==0,'exit_code':q.returncode,'groups':q.stdout.splitlines(),
 'scope':'actual inc four functions, original R7 read_status/get_budget, real candidate stop/suspend/resume; fake regmap/registration/PM boundaries',
 'tested_files':{n:sha(HERE/n) for n in [*pins,'samurai-usb-input-decode.h','test-backend.py','test-fixture.c']},
 'unchanged_R7_functions':['samurai_usb_read_status','samurai_usb_get_budget'],
 'actual_regmap_header_sha256':sha(regmap),'actual_regmap_inline_sha256':sha(out/'regmap-write-bits.actual.h'),
 'actual_fixture_sha256':sha(out/'actual-backend.c'),'command':cmd,
 'old_suites_rerun':False,'phone_accessed':False,'sdk':False,'physical_or_PD_permission_proved':False}
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
raise SystemExit(q.returncode)
