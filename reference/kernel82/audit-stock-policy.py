"""Reconstruct archived handset policy; run exact reader/classifier code offline.

This does not implement or authorize a charging controller. Generated C and
downloaded sources remain private. No device access is used by this script.
"""
from pathlib import Path
import hashlib, json, re, subprocess, tarfile, struct

OUT = Path('/mnt/e/edk2-samurai-out/kernel82')
STOCK = Path('/mnt/e/edk2-samurai-out/kernel76')
ARCHIVE = Path('/mnt/e/Realme X2 Pro移植主线Linux/artifacts/device/20261005T074931Z/live-device-tree.tar')
KERNEL = Path('/home/cy122/x2pro-linux/linux')
CHARGER = STOCK/'charging-research/stock--drivers--power--oppo--oppo_charger.c'
GAUGE = STOCK/'stock-oppo_bq27541.c'
CORE = KERNEL/'drivers/power/supply/bq27xxx_battery.c'
expected = {
    CHARGER: '57daaec681f55b35c01f2c0d5ecc7900650c13d032b0c676ca7ae86f183d33f4',
    GAUGE: 'c0c502065fcd46cc52173ab075074f3f3f66efe596f71845de0f8092291d5d84',
    CORE: 'b2cd415a995cb196559c0e4981988f737c17c98486449659d168314926aec69e',
    ARCHIVE: 'e3329db4f3568252286489abd2ae27b9cbd0c711a2c5d790ebfba80fffc5b56b',
}
for p,digest in expected.items():
    assert hashlib.sha256(p.read_bytes()).hexdigest()==digest, p

with tarfile.open(ARCHIVE) as tar:
    files={m.name.removeprefix('./'):tar.extractfile(m).read() for m in tar if m.isfile()}
node='soc/qcom,spmi@c440000/qcom,pm8150b@2/qcom,qpnp-smb5'
fields=['removed','cold','little_cold','cool','little_cool','normal','warm','hot']
policy={}
for key in fields:
    name=key+'_bat_decidegc'
    raw=files[node+'/qcom,'+name]
    assert len(raw)==4
    value=struct.unpack('>I',raw)[0]
    # Realme parser explicitly negates these two unsigned DT magnitudes.
    effective=-value if key in ('removed','cold') else value
    policy[name]={'raw_hex':raw.hex(),'u32_be':value,'parser_decidegrees_C':effective}
assert [policy[k+'_bat_decidegc']['parser_decidegrees_C'] for k in fields]==[-190,-20,0,50,120,160,440,530]

def function(path,name):
    source=path.read_text()
    m=re.search(r'^static (?:int|void) '+re.escape(name)+r'\([^;{}]*\)\s*\{',source,re.M)
    assert m, name
    pos=m.end(); depth=1
    while depth:
        if source[pos]=='{':depth+=1
        elif source[pos]=='}':depth-=1
        pos+=1
    return source[m.start():pos]

prelude=r'''
#include <stdbool.h>
#include <stdio.h>
#include <assert.h>
#include <errno.h>
#define dev_err(...) ((void)0)
#define ZERO_DEGREE_CELSIUS_IN_TENTH_KELVIN (-2731)
#define BQ27XXX_REG_TEMP 0x06
#define BQ27XXX_O_ZERO 1
static int mock_word, mock_error;
static bool allowed=true;
struct fake_gauge { int suspended,temp_pre; void *dev; struct {int reg_temp;} cmd_addr; };
static struct fake_gauge gauge={.cmd_addr={.reg_temp=6}};
static struct fake_gauge *gauge_ic=&gauge;
static int atomic_read(const int *v) {return *v;}
static bool oppo_vooc_get_allow_reading(void) {return allowed;}
static int bq27541_read_i2c(int reg,int *v) {assert(reg==6);*v=mock_word;return mock_error;}
struct bq27xxx_device_info {void *dev;int opts;};
union power_supply_propval {int intval;};
static int bq27xxx_read(struct bq27xxx_device_info *di,int reg,bool single)
{(void)di;assert(reg==6&&!single);return mock_error?mock_error:mock_word;}
enum {BATTERY_STATUS__HIGH_TEMP,BATTERY_STATUS__WARM_TEMP,BATTERY_STATUS__NORMAL,
BATTERY_STATUS__LITTLE_COOL_TEMP,BATTERY_STATUS__COOL_TEMP,BATTERY_STATUS__LITTLE_COLD_TEMP,
BATTERY_STATUS__COLD_TEMP,BATTERY_STATUS__LOW_TEMP,BATTERY_STATUS__REMOVED};
typedef int OPPO_CHG_TBATT_STATUS;
struct limits {int removed_bat_decidegc,cold_bat_decidegc,little_cold_bat_decidegc,
cool_bat_decidegc,little_cool_bat_decidegc,normal_bat_decidegc,warm_bat_decidegc,hot_bat_decidegc;};
struct oppo_chg_chip {int temperature,tbatt_status;bool batt_exist;struct limits limits;};
'''
functions='\n'.join([function(GAUGE,'bq27541_get_battery_temperature'),
                     function(CORE,'bq27xxx_battery_read_temperature'),
                     function(CHARGER,'oppo_chg_check_tbatt_status')])
limits=','.join(str(policy[k+'_bat_decidegc']['parser_decidegrees_C']) for k in fields)
body=r'''
int main(void) {
    struct bq27xxx_device_info di={0};
    union power_supply_propval value;
    int ret,result;
    mock_word=3037;mock_error=0;
    assert(bq27541_get_battery_temperature()==306);
    mock_error=-EIO;
    result=bq27541_get_battery_temperature();assert(result==306);printf("stock_first_error %d\n",result);
    result=bq27541_get_battery_temperature();assert(result==-400);printf("stock_second_error %d\n",result);
    allowed=false;assert(bq27541_get_battery_temperature()==-400);allowed=true;
    mock_error=0;mock_word=3038;assert(bq27541_get_battery_temperature()==307);
    gauge.suspended=1;mock_word=3100;assert(bq27541_get_battery_temperature()==307);gauge.suspended=0;
    for(int i=0;i<2;i++) {
        mock_error=i?-EREMOTEIO:-EIO;value.intval=12345;
        ret=bq27xxx_battery_read_temperature(&di,&value);
        assert(ret==mock_error&&value.intval==12345);printf("kernel_error %d output_unchanged %d\n",ret,value.intval);
    }
    mock_error=0;mock_word=3037;ret=bq27xxx_battery_read_temperature(&di,&value);
    assert(ret==0&&value.intval==306);printf("kernel_valid %d %d\n",ret,value.intval);
    struct oppo_chg_chip chip={.limits={LIMIT_VALUES}};
    const int samples[]={-401,-191,-190,-189,-21,-20,-19,-1,0,1,49,50,51,119,120,121,159,160,161,439,440,441,529,530,531};
    for(unsigned i=0;i<sizeof(samples)/sizeof(samples[0]);i++) {
        chip.temperature=samples[i];oppo_chg_check_tbatt_status(&chip);
        printf("classification %d %d %d\n",samples[i],chip.tbatt_status,chip.batt_exist);
    }
    return 0;
}
'''.replace('LIMIT_VALUES',limits)
generated=OUT/'private-reader-harness.c'
generated.write_text(prelude+functions+'\n'+body)
exe=OUT/'private-reader-harness'
subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-O2',str(generated),'-o',str(exe)],check=True)
run=subprocess.run([str(exe)],capture_output=True,text=True,check=True)
(OUT/'reader-harness-output.txt').write_text(run.stdout)
labels=['high','warm','normal','little_cool','cool','little_cold','cold','low','removed']
samples=[]
for line in run.stdout.splitlines():
    if line.startswith('classification '):
        _,temp,state,present=line.split()
        samples.append({'decidegrees_C':int(temp),'stock_initial_classification':labels[int(state)],'stock_batt_exist':bool(int(present))})
assert len(samples)==25
assert next(x for x in samples if x['decidegrees_C']==-20)['stock_initial_classification']=='cold'
assert next(x for x in samples if x['decidegrees_C']==530)['stock_initial_classification']=='warm'
assert next(x for x in samples if x['decidegrees_C']==531)['stock_initial_classification']=='high'
gauge_source=GAUGE.read_text()
assert 'gauge_ic->batt_vol_pre = gauge_ic->batt_cell_max_vol;' in gauge_source
raw_parameters={}
for name in ['vbatt_num','input_current_usb_ma','max_chg_time_sec','temp_normal_vfloat_mv','normal_vfloat_over_sw_limit','vbatt_hv_thr']:
    raw=files[node+'/qcom,'+name]
    raw_parameters[name]={'raw_hex':raw.hex(),'u32_be':struct.unpack('>I',raw)[0]}
result={
    'scope':'Offline exact-source fault/classification tests and same-handset archived DT decoding; not charging acceptance.',
    'source_sha256':{p.name:d for p,d in expected.items()},
    'temperature_policy':policy,'raw_parameters':raw_parameters,
    'CONFIG_HIGH_TEMP_VERSION_stock_runtime_value_verified':False,
    'policy_decoding_assumes_normal_parser_branch':True,
    'source_classifier_boundary_samples':samples,
    'source_function_test_output':run.stdout.splitlines()[:5],
    'stock_error_policy':'First temperature read error returns cached value; second consecutive error returns -400 decidegrees C.',
    'kernel_error_policy':'TEMP reads the register directly; read error returned as errno, output invalid. 360s poll interval is not TEMP sample age.',
    'stock_dual_cell_voltage_policy_uses_max_cell':True,
    'current_mainline_voltage_is_pack_uV':True,
    'hysteresis_and_full_controller_exercised':False,
    'hardware_faults_injected':False,'device_access':False,'charge_control_writes':False,
}
(OUT/'stock-policy-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print('Offline exact-source tests passed; 25 classification samples; fault reads return expected results.')
print(json.dumps({'temperature_policy':policy,'raw_parameters':raw_parameters},indent=2))
