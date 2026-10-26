from pathlib import Path
import json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;work=P/'ipe-quiesce';work.mkdir(exist_ok=True)
prefix=r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint32_t u32;
#define __iomem
#define BIT(n) (1U<<(n))
#define EXPORT_SYMBOL_GPL(x)
struct camss_a5_resources {void *dev,*sierra,*ipe[2];unsigned enabled_groups,held_domains,ipe_reset_acks[2];};
static u32 registers[3][0x2000/4];static unsigned writes,clears[2][2],resets[2][2],mode;
static u32 readl(void *p){return *(u32*)p;}
static void writel(u32 value,void *p){
 unsigned engine=(u32*)p>=registers[2]?1:0;u32 *base=registers[engine+1];unsigned off=((u32*)p-base)*4;assert(engine<2);writes++;
 unsigned block=off>=0x1000;unsigned status=block?0x100c:0x44;
 if(off==0x38 || off==0x101c){assert(value==1 && base[(block?0x1014:0x34)/4]==1);clears[engine][block]++;if(mode!=1+engine*2+block)base[status/4]&=~1U;}
 else if(off==0x10 || off==0x1008){assert(value==(block?3U:15U) && clears[engine][block] && !(base[status/4]&1));resets[engine][block]++;if(mode!=5+engine*2+block)base[status/4]|=1;}
 else assert(off==0x34 || off==0x1014);
 *(u32*)p=value;
}
#define readl_poll_timeout(addr,value,condition,interval,timeout) ({(void)(interval);(void)(timeout);value=readl(addr);(condition)?0:-ETIMEDOUT;})
'''
main=r'''
int main(void){
 struct camss_a5_resources r={.dev=&r,.sierra=registers[0],.ipe={registers[1],registers[2]},.enabled_groups=15,.held_domains=7};unsigned cases=0;
 assert(camss_a5_ipe_quiesce(NULL)==-EINVAL && !writes);cases++;
 for(unsigned trial=0;trial<9;trial++){
  mode=trial;writes=0;memset(registers,0,sizeof(registers));memset(clears,0,sizeof(clears));memset(resets,0,sizeof(resets));
  for(unsigned i=1;i<3;i++){registers[i][0x44/4]=1;registers[i][0x100c/4]=1;}
  int ret=camss_a5_ipe_quiesce(&r);assert(ret==(trial?-ETIMEDOUT:0));
  for(unsigned i=0;i<2;i++)for(unsigned j=0;j<2;j++){
   unsigned bit=1U<<j;bool bad=trial==1+i*2+j || trial==5+i*2+j;
   assert(!!(r.ipe_reset_acks[i]&bit)==!bad);assert(resets[i][j]==(trial==1+i*2+j?0U:1U));
  }
  assert(r.enabled_groups==15 && r.held_domains==7);cases++;
 }
 mode=0;writes=0;registers[0][0x08/4]=1<<9;assert(camss_a5_ipe_quiesce(&r)==-EBUSY && !writes);registers[0][0x08/4]=0;cases++;
 for(unsigned bit=0;bit<4;bit++)if(bit!=1){r.enabled_groups=15&~(1U<<bit);assert(camss_a5_ipe_quiesce(&r)==-EHOSTDOWN && !writes);cases++;}r.enabled_groups=15;
 for(unsigned bit=1;bit<3;bit++){r.held_domains=7&~(1U<<bit);assert(camss_a5_ipe_quiesce(&r)==-EHOSTDOWN && !writes);cases++;}r.held_domains=7;
 printf("QUIESCE_CASES %u\n",cases);return 0;
}
'''
(work/'probe.c').write_text(prefix+(HERE/'ipe-quiesce.c').read_text()+main)
q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-fsanitize=address,undefined',str(work/'probe.c'),'-o',str(work/'probe')],capture_output=True);assert not q.returncode,q.stderr.decode()
q=subprocess.run([str(work/'probe')],capture_output=True);(work/'result-private.log').write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
assert q.stdout==b'QUIESCE_CASES 16\n'
report=dict(stage=381,actual_new_ipe_quiesce_body=True,tests=16,asan_ubsan=True,stale_ack_cleared_and_zero_observed_before_each_reset=True,
 reset_ack_and_post_ack_clear_required=True,cdm_failure_does_not_skip_top_or_second_engine=True,live_a5_or_missing_power_rejected_without_mmio_writes=True,
 clocks_and_domains_not_released_by_reset_helper=True,registers_and_power_modelled=True,hardware_execution=False,passed=True)
(HERE/'ipe-quiesce-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
