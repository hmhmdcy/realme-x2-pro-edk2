"""Run the OEM voltage writer with captured I/O, then derive equivalent mainline constraints."""
from pathlib import Path
import hashlib,json,re,subprocess,os
ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel192')
oem=Path('/home/cy122/workspace/realmeX2pro-AndroidR-droidspaces/source/drivers/regulator/qcom_pm8008-regulator.c');text=oem.read_text()
name='static int pm8008_write_voltage(';start=text.index(name);brace=text.index('{',start);depth=1;i=brace+1
while depth:
 depth+=(text[i]=='{')-(text[i]=='}');i+=1
function=text[start:i]
constants={name:int(re.search(r'^#define\s+'+name+r'\s+(\d+)\s*$',text,re.M).group(1)) for name in ['VSET_STEP_SIZE_MV','VSET_STEP_MV']}
assert constants==dict(VSET_STEP_SIZE_MV=1,VSET_STEP_MV=8)
assert 'mv = DIV_ROUND_UP(DIV_ROUND_UP(mv, VSET_STEP_MV) * VSET_STEP_MV,' in function
source='''#include <stdint.h>
#include <stdio.h>
#include <errno.h>
typedef uint8_t u8;
struct pm8008_regulator { void *regmap; unsigned base; };
#define DIV_ROUND_UP(n,d) (((n)+(d)-1)/(d))
#define VSET_STEP_MV 8
#define VSET_STEP_SIZE_MV 1
#define LDO_VSET_LB_REG(base) ((base)+0x40)
#define pm8008_err(...) ((void)0)
#define pm8008_debug(...) ((void)0)
static int written, writes;
static int pm8008_write(void *map, unsigned reg, const u8 *data, int count) {
 (void)map;
 if (reg!=0x4140 || count!=2) return -EINVAL;
 written=data[0] | data[1]<<8; writes++; return 0;
}
'''+function+'''
int main(void) {
 struct pm8008_regulator r={.base=0x4100};
 int requests[]={1050000,1100000,1800000,2800000};
 int expected[]={1056,1104,1800,2800};
 for (unsigned i=0;i<sizeof(requests)/sizeof(requests[0]);i++) {
  int before=writes; int rc=pm8008_write_voltage(&r,requests[i],requests[i]);
  if (rc || writes!=before+1 || written!=expected[i]) return 1;
  printf("%d %d\\n",requests[i],written*1000);
 }
 int before=writes;
 if (pm8008_write_voltage(&r,1050001,1050001)!=-EINVAL || writes!=before) return 2;
 return 0;
}
'''
c=out/'oem-voltage-writer-host-private.c';c.write_text(source);exe=out/'oem-voltage-writer-host-private'
result=subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(c),'-o',str(exe)],capture_output=True,text=True);assert result.returncode==0,result.stderr
run=subprocess.run([str(exe)],capture_output=True,text=True,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=1:abort_on_error=1',UBSAN_OPTIONS='halt_on_error=1'));assert run.returncode==0 and not run.stderr,run.stderr
(out/'oem-voltage-writer-host-private.log').write_text(run.stdout+run.stderr)
results=[dict(stock_requested_min_uv=int(a),stock_requested_max_uv=int(a),oem_programmed_uv=int(b)) for a,b in (line.split() for line in run.stdout.splitlines())]
for r in results:
 available=list(range(528000,1504000+1,8000)) if r['stock_requested_min_uv']<1504000 else list(range(1504000,3400000+1,8000))
 exact=[v for v in available if r['stock_requested_min_uv']<=v<=r['stock_requested_max_uv']]
 equivalent=[v for v in available if r['stock_requested_min_uv']<=v<=r['oem_programmed_uv']]
 assert equivalent==[r['oem_programmed_uv']]
 r.update(mainline_exact_constraint_valid=bool(exact),equivalent_mainline_min_uv=r['stock_requested_min_uv'],equivalent_mainline_max_uv=r['oem_programmed_uv'])
report=dict(stage=192,oem_source_sha256=hashlib.sha256(oem.read_bytes()).hexdigest(),oem_production_function_executed_with_captured_writes=True,hardware_access=False,asan_ubsan_passed=True,stock_max_checked_before_rounding=True,voltages=results,analog_voltage_measured=False)
(ref/'pmic-voltage-contract-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
