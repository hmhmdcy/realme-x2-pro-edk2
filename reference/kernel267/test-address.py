"""Run existing address fault cases against the new common MFD functions."""
from pathlib import Path
import ast
import hashlib
import json
import os
import resource
import subprocess

R=Path(__file__).resolve().parent
P=Path('/mnt/e/edk2-samurai-out/kernel267/address-tests-r1');P.mkdir(mode=0o700)
s=(R/'qcom-pm8008.c').read_text()
def fn(name):
    pos=s.index(name+'(');start=s.rfind('\nstatic ',0,pos)+1
    body=s.index('{',pos);depth=1;end=body+1
    while depth:depth+=(s[end]=='{')-(s[end]=='}');end+=1
    return s[start:end]+'\n'
tree=ast.parse((R.parent/'kernel195/test-pmic-address.py').read_text());old={}
for item in tree.body:
    if isinstance(item,ast.Assign) and isinstance(item.value,ast.Constant) and isinstance(item.value.value,str):
        for target in item.targets:
            if isinstance(target,ast.Name):old[target.id]=item.value.value
stub=old['stub']+'\nstruct pm8008_reset { struct device *dev; struct gpio_desc *gpio,*blocker; };\n'
block='\n#define PM8008_FACTORY_ADDRESS 8\n#define PM8008_ASSIGNED_ADDRESS 4\n#define PM8008_SID_CONFIG 0x0644\n'
block+=''.join(fn(n) for n in ['pm8008_has_reset','pm8008_set_reset','pm8008_read_identity','pm8008_initialize_address'])
tests=old['tests'].split(' start();get_error=-517;')[0]
tests=tests.replace('pm8008_initialize_address(&client,g)','pm8008_initialize_address(&client,&(struct pm8008_reset){.gpio=g})')
tests+='\n printf("{\\"passed\\":true,\\"address_cases\\":%d}\\n",cases);return 0;}\n'
body=stub+block+tests
variants={'actual':body,
          'no-failed-address-reset':body.replace('if (ret && release_attempted)', 'if (0 && ret && release_attempted)')}
def no_core():resource.setrlimit(resource.RLIMIT_CORE,(0,0))
results={}
for name,text in variants.items():
    p=P/(name+'.c');p.write_text(text);binary=p.with_suffix('')
    q=subprocess.run(['gcc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-variable',
                     '-fsanitize=address,undefined','-fno-omit-frame-pointer','-g',str(p),'-o',str(binary)],capture_output=True)
    (P/(name+'-compile-private.log')).write_bytes(q.stdout+q.stderr)
    assert q.returncode==0,q.stderr.decode()[-1500:]
    q=subprocess.run([str(binary)],capture_output=True,preexec_fn=no_core,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=1'))
    (P/(name+'-run-private.log')).write_bytes(q.stdout+q.stderr)
    if name=='actual':
        assert q.returncode==0 and not q.stderr,q.stderr.decode()[-1500:]
        results[name]=json.loads(q.stdout)
    else:
        assert q.returncode!=0 and b'Assertion' in q.stderr
        results[name]=dict(rejected=True)
report=dict(stage=267,actual_common_mfd_functions_extracted=True,asan_ubsan=True,
            source_sha256=hashlib.sha256(s.encode()).hexdigest(),results=results,
            no_hardware_or_real_devres_concurrency_test=True)
(R/'address-test-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
