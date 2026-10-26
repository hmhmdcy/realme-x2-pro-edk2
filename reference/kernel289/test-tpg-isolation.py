"""Exercise actual gen2 RX/TPG functions across external PHY histories under sanitizers."""
from pathlib import Path
import hashlib,json,re,subprocess
import host

ROOT=Path(__file__).resolve().parent
source=Path('/home/cy122/x2pro-linux/camera279-isp-kernel/drivers/media/platform/qcom/camss/camss-csid-gen2.c').read_text()
def function(name):
 start=source.index('static void '+name+'(');opening=source.index('{',start);depth=0
 for i in range(opening,len(source)):
  if source[i]=='{':depth+=1
  elif source[i]=='}':
   depth-=1
   if not depth:return source[start:i+1]
 raise AssertionError(name)
defines='\n'.join(re.findall(r'^#define[^\n]*',source.replace('\\\n',''),re.M))
harness=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint8_t u8;typedef uint32_t u32;
#define BIT(n) (1u<<(n))
#define MSM_CSID_PAD_FIRST_SRC 1
struct csid_phy_config {u8 lane_cnt,csiphy_id;u32 lane_assign;bool is_cphy;};
struct csid_testgen_config {unsigned mode;bool enabled;};
struct v4l2_mbus_framefmt {u32 code,width,height;};
struct csid_format_info {u32 data_type,decode_format;};
struct formats {struct csid_format_info *formats;unsigned nformats;};
struct resource {struct formats *formats;};
struct csid_device {struct csid_phy_config phy;struct csid_testgen_config testgen;struct v4l2_mbus_framefmt fmt[5];struct resource *res;unsigned char *base;};
static const struct csid_format_info *csid_get_fmt_entry(struct csid_format_info *f,unsigned n,u32 code){assert(n==1&&code==0x300a);return f;}
static void writel_relaxed(u32 value,void *p){memcpy(p,&value,sizeof(value));}
static u32 reg(struct csid_device *c,unsigned offset){u32 v;memcpy(&v,c->base+offset,4);return v;}
'''+defines+'\n'+function('__csid_configure_rx')+'\n'+function('__csid_configure_testgen')+r'''
int main(void){
 unsigned char memory[0x1000]={0};struct csid_format_info fi={.data_type=0x2b,.decode_format=2};struct formats formats={&fi,1};struct resource resource={&formats};
 struct csid_device c={.base=memory,.res=&resource,.testgen={.mode=9}};
 c.fmt[4]=(struct v4l2_mbus_framefmt){.code=0x300a,.width=320,.height=240};
 uint64_t cases=0;
 for(unsigned lanes=0;lanes<=4;lanes++)for(unsigned cphy=0;cphy<2;cphy++)for(unsigned id=0;id<4;id++)for(unsigned assign=0;assign<65536;assign++){
  c.phy=(struct csid_phy_config){.lane_cnt=lanes,.csiphy_id=id,.lane_assign=assign,.is_cphy=cphy};
  c.testgen.enabled=false;__csid_configure_rx(&c,&c.phy,0);
  u32 expected=((lanes?lanes:4)-1)|(assign<<4)|(id<<20)|(cphy<<24);
  assert(reg(&c,0x100)==expected&&reg(&c,0x104)==0x41);
  c.testgen.enabled=true;__csid_configure_rx(&c,&c.phy,0);
  assert(reg(&c,0x100)==0x32103&&reg(&c,0x104)==0x41);
  __csid_configure_testgen(&c,1,3,0);
  assert(reg(&c,0x600)==0xa06437&&reg(&c,0x610)==0x14000f0&&reg(&c,0x614)==0x2b&&reg(&c,0x618)==0x20be8);
  assert(c.phy.lane_cnt==lanes&&c.phy.csiphy_id==id&&c.phy.lane_assign==assign&&c.phy.is_cphy==(bool)cphy);
  cases++;
 }
 c.testgen.enabled=true;__csid_configure_rx(&c,&c.phy,4);assert(reg(&c,0x104)==0x45);
 __csid_configure_testgen(&c,0,3,0);assert(reg(&c,0x600)==0xa06436);
 printf("GEN2_TPG_EXTERNAL_HISTORY_CASES=%llu PASS\n",(unsigned long long)cases);return 0;
}
'''
p=host.PRIVATE/'tpg-isolation-tests-private.c';p.write_text(harness)
binary=host.PRIVATE/'tpg-isolation-tests-private'
q=subprocess.run(['gcc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(p),'-o',str(binary)],capture_output=True)
log=host.PRIVATE/'tpg-isolation-test-compile-private.log'
if log.exists() and not log.with_suffix('.log.attempt1').exists():log.with_suffix('.log.attempt1').write_bytes(log.read_bytes())
log.write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
q=subprocess.run([str(binary)],capture_output=True,timeout=45)
(host.PRIVATE/'tpg-isolation-tests-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stderr.decode()
report=dict(stage=289,exit=q.returncode,asan_ubsan=True,actual_functions=['__csid_configure_rx','__csid_configure_testgen'],
 phy_histories=2621440,internal_tpg_dphy_four_lanes_independent=True,external_cphy_dphy_preserved=True,
 physical_configuration_not_mutated=True,vc_and_disable_checked=True,source_sha256=hashlib.sha256(source.encode()).hexdigest(),harness_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),hardware_candidate_not_deployed=True)
(ROOT/'tpg-isolation-host-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(q.stdout.decode());print(json.dumps(report,indent=2))
