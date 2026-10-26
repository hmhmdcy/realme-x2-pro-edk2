from pathlib import Path
import hashlib,json,re,subprocess,tempfile
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'usb-input-irq-wake-candidate'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def function(text,name):
    match=re.search(r'(?m)^(?:static )?(?:int|void|irqreturn_t) '+name+r'\([^;]*?\)\n\{',text);assert match,name
    end=match.end();depth=1
    while depth:depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[match.start():end]+'\n'
def clean(text):return '\n'.join(line for line in text.splitlines() if not line.startswith('#include'))+'\n'
source=(HERE/'samurai-usb-input.c').read_text();baseline=(OLD/'samurai-usb-input.c').read_text();backend=(HERE/'samurai-apsd-input.inc').read_text()
names=['samurai_usb_changed','samurai_usb_set_property','samurai_usb_stop','samurai_usb_clear_wake','samurai_usb_arm_wake',
    'samurai_usb_restart_work','samurai_usb_cleanup_wake','samurai_usb_suspend','samurai_usb_resume','samurai_usb_prepare',
    'samurai_usb_complete','samurai_usb_event','samurai_usb_request_events','samurai_usb_shutdown']
unchanged=[name for name in names if name not in ['samurai_usb_stop','samurai_usb_prepare','samurai_usb_complete']]
assert all(function(source,name)==function(baseline,name) for name in unchanged)
probe=function(source,'samurai_usb_probe');assert probe.index('devm_power_supply_register')<probe.index('dev, samurai_usb_cleanup_wake')<probe.index('dev, samurai_usb_stop')<probe.index('samurai_usb_apsd_start')
fixture=(OLD/'test-wake.c').read_text()
original=re.search(r'(?ms)^struct samurai_usb_input \{.*?^\};',fixture).group()
structure=re.search(r'(?ms)^struct samurai_usb_input \{.*?^\};',source).group()
api='#define IS_ENABLED(x) 1\ntypedef unsigned long long u64;\ntypedef unsigned char u8;\n'+clean((HERE/'samurai-apsd-backend.h').read_text())
fixture=fixture.replace(original,api+'\n'+(HERE/'samurai-usb-input-decode.h').read_text()+'\n'+structure)
fixture=fixture.replace('static bool fire_probe_irq;','static bool fire_probe_irq,apsd_backend;\nstatic int registrations,withdrawals;')
edge='''
static int no_read(void *ctx,struct samurai_apsd_bus_sample *sample){return -EOPNOTSUPP;}
static int no_write(void *ctx,const struct samurai_apsd_attempt *attempt,struct samurai_apsd_transfer_result *result){return -EOPNOTSUPP;}
static const struct samurai_apsd_bus_ops samurai_usb_apsd_ops={no_read,no_write};
int samurai_apsd_bus_register(struct device *dev,const struct samurai_apsd_bus_ops *ops,void *ctx)
{assert(dev==input.event_dev&&ctx==&input&&ops==&samurai_usb_apsd_ops&&!input.lock.held&&!input.paused&&!input.pm_prepared);registrations++;return 0;}
void samurai_apsd_bus_unregister(struct device *dev,void *ctx)
{assert(dev==input.event_dev&&ctx==&input&&!input.lock.held&&input.apsd_joining&&(input.paused||input.pm_prepared));withdrawals++;}
'''
functions=function(backend,'samurai_usb_apsd_start')+function(backend,'samurai_usb_apsd_withdraw')+'\n'.join(function(source,name) for name in names)
fixture=fixture.replace('#include "actual-functions.inc"',edge+functions)
fixture=fixture.replace('fire_probe_irq=false;','fire_probe_irq=apsd_backend=false;registrations=withdrawals=0;')
fixture=fixture.replace(' assert(groups==10);', (HERE/'test-pm.inc').read_text()+'\n assert(groups==15);')
fixture=fixture.replace('10 IRQ-wake lifecycle groups passed','15 current IRQ/PM/APSD lifecycle groups passed')
flags=['-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-sign-compare','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie']
with tempfile.TemporaryDirectory(prefix='samurai-APSD-current-PM-') as directory:
    root=Path(directory);code=root/'actual.c';code.write_text(fixture);binary=root/'test'
    built=subprocess.run(['gcc',*flags,str(code),'-o',str(binary)],capture_output=True,text=True);assert built.returncode==0,built.stderr
    child=subprocess.run([str(binary)],capture_output=True,text=True,timeout=30);assert child.returncode==0,(child.returncode,child.stdout,child.stderr)
    assert '15 current IRQ/PM/APSD lifecycle groups passed' in child.stdout and not child.stderr
result=dict(passed=True,groups=15,actual_functions=names+['samurai_usb_apsd_start','samurai_usb_apsd_withdraw'],
    unchanged_current_IRQ_PM_functions=unchanged,owner_registry_and_IRQ_APIs_modeled=True,
    current_devres_order_retained=True,fixture_sha256=sha(fixture.encode()),flags=flags,
    files={name:sha((HERE/name).read_bytes()) for name in ['samurai-usb-input.c','samurai-apsd-input.inc','samurai-apsd-backend.h','samurai-usb-input-decode.h','test-pm.inc','run-pm-tests.py']},
    phone_accessed=False,physical_USB_wakeup_verified=False)
with (HERE/'pm-test-result.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(dict(passed=True,groups=15,phone_accessed=False)))
