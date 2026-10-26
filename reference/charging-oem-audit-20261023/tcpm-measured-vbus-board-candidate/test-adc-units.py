"""Run actual ADC5 scale and processed-reader bodies without touching hardware."""
from pathlib import Path
import hashlib,json,re,subprocess,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
BASE=Path('/home/cy122/charging-management-20261023/gauge-image502-notify-01/source354')
OUT=Path('/home/cy122/charging-management-20261023/tcpm-adc5-unit-tests-02')
sha=lambda b:hashlib.sha256(b).hexdigest()

def definition(source,name):
    matches=list(re.finditer(r'^static int '+name+r'\([^;]*?\n\{',source,re.M))
    assert len(matches)==1,name
    start=matches[0].start();end=source.index('\n}\n',start)+3
    return source[start:end]

def main():
    common_path=BASE/'drivers/iio/adc/qcom-vadc-common.c'
    driver_path=BASE/'drivers/iio/adc/qcom-spmi-adc5.c'
    binding_path=BASE/'include/dt-bindings/iio/qcom,spmi-vadc.h'
    common=common_path.read_text();driver=driver_path.read_text();bindings=binding_path.read_text()
    assert re.search(r'#define ADC5_USB_IN_V_16\s+0x08\b',bindings)
    assert '[ADC5_USB_IN_V_16]\t= ADC5_CHAN_VOLT("usb_in_v_div_16", 8,' in driver
    assert '.full_scale_code_volt = 0x70e4,' in driver
    assert 'prescale_index' in driver and 'SCALE_HW_CALIB_DEFAULT' in driver
    funcs=[definition(common,'qcom_vadc_scale_code_voltage_factor'),
           definition(common,'qcom_vadc_scale_hw_calib_volt')]
    ratios=re.search(r'static const struct u32_fract adc5_prescale_ratios\[\] = \{.*?\n\};',common,re.S)
    assert ratios
    read=definition(driver,'adc_read_raw_common')
    assert 'return IIO_VAL_INT;' in read and '/ 1000' not in read
    # Boundaries: structures, conversion, the dispatch to the selected default
    # scaler. The selected scaler and the driver's complete reader are actual C.
    prefix=r'''
#include <stdint.h>
#include <errno.h>
#include <assert.h>
#include <stdio.h>
typedef uint16_t u16;
typedef int64_t s64;
struct u32_fract { unsigned int numerator, denominator; };
struct adc5_data { unsigned int full_scale_code_volt; };
struct adc5_channel_prop { unsigned int scale_fn_type, prescale; };
struct adc5_chip { struct adc5_channel_prop *chan_props; const struct adc5_data *data; };
struct iio_dev { struct adc5_chip *private; };
struct iio_chan_spec { unsigned int address; };
typedef int (*adc_do_conversion)(struct adc5_chip *, struct adc5_channel_prop *,
        const struct iio_chan_spec *, u16 *, u16 *);
#define VADC5_MAX_CODE 0x7fff
#define IIO_CHAN_INFO_PROCESSED 42
#define IIO_VAL_INT 1
static s64 div64_s64(s64 a, s64 b) { return a/b; }
static struct adc5_chip *iio_priv(struct iio_dev *d) { return d->private; }
'''
    dispatch=r'''
static int qcom_adc5_hw_scale(unsigned int type, unsigned int prescale,
        const struct adc5_data *data, u16 raw, int *uv)
{
    assert(type==0 && prescale==8);
    return qcom_vadc_scale_hw_calib_volt(&adc5_prescale_ratios[prescale],data,raw,uv);
}
static u16 code;
static int conversion_error;
static int convert(struct adc5_chip *a, struct adc5_channel_prop *p,
        const struct iio_chan_spec *c, u16 *v, u16 *i)
{ (void)a; (void)p; (void)c; (void)i; *v=code; return conversion_error; }
'''
    main_c=r'''
int main(void)
{
    const struct adc5_data data = {0x70e4};
    struct adc5_channel_prop prop = {.scale_fn_type=0,.prescale=8};
    struct adc5_chip chip = {&prop,&data};
    struct iio_dev dev = {&chip};
    const struct iio_chan_spec channel = {.address=0};
    const u16 raw[] = {0,2890,4817,8670,0x70e4,0xffff};
    const int expected[] = {0,3000000,5000336,9000000,30000000,0};
    int uv,unused,cases=0;
    for (unsigned int n=0;n<sizeof(raw)/sizeof(raw[0]);n++) {
        code=raw[n];uv=-1;
        assert(adc_read_raw_common(&dev,&channel,&uv,&unused,IIO_CHAN_INFO_PROCESSED,convert)==IIO_VAL_INT);
        assert(uv==expected[n]);cases++;
    }
    conversion_error=-EIO;uv=123;
    assert(adc_read_raw_common(&dev,&channel,&uv,&unused,IIO_CHAN_INFO_PROCESSED,convert)==-EIO && uv==123);cases++;
    assert(adc_read_raw_common(&dev,&channel,&uv,&unused,0,convert)==-EINVAL);cases++;
    printf("{\"passed\":true,\"cases\":%d,\"raw8670_processed\":9000000,\"unit\":\"uV\"}\n",cases);
    return 0;
}
'''
    assert not OUT.exists(),'Inspect prior test result rather than overwriting it'
    OUT.mkdir(mode=0o700);c=OUT/'test.c';c.write_text(prefix+ratios.group()+'\n'.join(funcs)+dispatch+read+main_c)
    # Linux's callback deliberately leaves val2 unused for IIO_VAL_INT.
    argv=['cc','-std=c11','-g','-Wall','-Wextra','-Werror','-Wno-unused-parameter',
          '-fsanitize=address,undefined',str(c),'-o',str(OUT/'test')]
    build=subprocess.run(argv,capture_output=True,text=True);(OUT/'build.stderr').write_text(build.stderr)
    assert build.returncode==0,build.stderr
    run=subprocess.run([str(OUT/'test')],capture_output=True,text=True)
    (OUT/'run.stdout').write_text(run.stdout);(OUT/'run.stderr').write_text(run.stderr)
    assert run.returncode==0,run.stdout+run.stderr
    result=dict(passed=True,result=json.loads(run.stdout),command=argv,actual_functions=
        ['qcom_vadc_scale_code_voltage_factor','qcom_vadc_scale_hw_calib_volt','adc_read_raw_common'],
        sources={str(p.relative_to(BASE)):sha(p.read_bytes()) for p in [common_path,driver_path,binding_path]},
        test_source_sha256=sha(c.read_bytes()),ADC_channel=8,prescale=[1,16],processed_unit='uV',
        processed_scale_1000_would_be_wrong=True,phone_accessed=False,physical_accuracy_verified=False)
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    with (HERE/'adc-unit-result.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result))

if __name__=='__main__':main()
