"""Exercise the actual new reset/profile gate, retaining232 supplier mocks."""
from pathlib import Path
import ast
import hashlib
import json
import resource
import subprocess

R = Path(__file__).resolve().parent
P = Path('/mnt/e/edk2-samurai-out/kernel235/mfd-profile-tests-r2')
P.mkdir(mode=0o700)
source = (R / 'qcom-pm8008.c').read_text()
tree = ast.parse((R.parent / 'kernel232/test-reset-address.py').read_text())
assignments = {t.id: n.value for n in tree.body if isinstance(n, ast.Assign)
               for t in n.targets if isinstance(t, ast.Name)}
common = ast.literal_eval(assignments['common'])
stub = common + ast.literal_eval(assignments['orchestration_stub'].right)
stub = stub.replace('struct i2c_client { struct device dev; int addr; };',
                    'struct i2c_client { struct device dev; int addr,irq; };')
stub += '''
static void dev_set_drvdata(struct device *d,void *data) { (void)d;assert(data==&allocated); }
#define PM8008_FACTORY_ADDRESS 8
static bool experimental_p_imx319_power;
static bool marker;
static bool of_machine_is_compatible(const char *name) { assert(!strcmp(name,"realme,samurai"));return true; }
static bool device_property_present(struct device *dev,const char *name) {
 (void)dev;assert(!strcmp(name,"realme,imx319-power-lab"));return marker;
}
'''


def function(name):
    pos = source.index(name + '(')
    start = source.rfind('\nstatic ', 0, pos) + 1
    end = source.index('{', pos) + 1
    depth = 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end] + '\n'


code = function('pm8008_hold_reset') + function('pm8008_reset_and_address')
main = r'''
static void start(void) {
 static_error=get_error=action_error=link_error=init_error=id_error=reset_error=0;
 reset_calls=id_calls=init_calls=get_calls=node_puts=action_set=link_count=0;action=NULL;
}
int main(void) {
 unsigned int cases=0;struct i2c_client c={.addr=8};
 for(unsigned int flags=0;flags<4;flags++)for(unsigned int present=0;present<2;present++)
 for(unsigned int property=0;property<2;property++)for(unsigned int irq=0;irq<2;irq++) {
  start();is_p=present;marker=property;c.irq=irq;
  experimental_p_address_only=flags&1;experimental_p_imx319_power=!!(flags&2);
  int expected=!present?-EINVAL:(flags==0||flags==3)?-EOPNOTSUPP:
    (experimental_p_imx319_power!=marker||(experimental_p_imx319_power&&irq))?-EINVAL:0;
  assert(pm8008_reset_and_address(&c)==expected);
  if(expected)assert(!get_calls&&!reset_calls&&!init_calls&&!id_calls);
  else {assert(get_calls==1&&init_calls==1&&id_calls==1&&action_set==1);action(action_data);}
  assert(!pm8008_address_lock.depth);cases++;
 }
 c.addr=4;is_p=0;marker=false;
 for(unsigned int flags=0;flags<4;flags++)for(unsigned int irq=0;irq<2;irq++) {
  start();c.irq=irq;experimental_p_address_only=flags&1;experimental_p_imx319_power=!!(flags&2);
  assert(pm8008_reset_and_address(&c)==0);
  assert(get_calls==1&&init_calls==1&&!id_calls&&!reset_calls&&!action_set);cases++;
 }
 printf("{\"cases\":%u,\"passed\":true}\n",cases);return 0;
}
'''
variants = {'current': code,
            'missing_factory_p_guard': code.replace('if (of_machine_is_compatible("realme,samurai") &&\n\t    client->addr == PM8008_FACTORY_ADDRESS && !supplier)', 'if (false)'),
            'missing_profile_exclusivity': code.replace('if (experimental_p_address_only == experimental_p_imx319_power)', 'if (false)')}
results = {}
for name, body in variants.items():
    assert name == 'current' or body != code
    path = P / (name + '.c')
    path.write_text(stub + body + main)
    binary = P / name
    build = subprocess.run(['gcc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function', '-Wno-unused-variable',
                            '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-g', str(path), '-o', str(binary)], capture_output=True)
    (P / (name + '-compile-private.log')).write_bytes(build.stdout + build.stderr)
    assert build.returncode == 0, build.stderr.decode()[-1400:]
    def limit():
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    run = subprocess.run([str(binary)], capture_output=True, preexec_fn=limit)
    (P / (name + '-run-private.log')).write_bytes(run.stdout + run.stderr)
    if name == 'current':
        assert run.returncode == 0 and not run.stderr, run.stderr.decode()[-1400:]
        results[name] = json.loads(run.stdout)
        assert results[name]['cases'] == 40
    else:
        assert run.returncode == -6 and b'Assertion' in run.stderr
        results[name] = dict(counterexample_rejected=True)
report = dict(stage=235, actual_orchestration_function=True, asan_ubsan_passed=True,
              results=results, source_sha256=hashlib.sha256(source.encode()).hexdigest(),
              q_orchestration_path_preserved=True, factory_p_cannot_fall_back_to_seven_cells=True,
              real_device_core_and_mfd_cell_allocation_not_modeled=True, phone_unchanged=True)
(R / 'mfd-profile-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
