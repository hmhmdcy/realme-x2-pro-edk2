from pathlib import Path
import json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;work=P/'sid-regression';work.mkdir(exist_ok=True)
s=(P/'camss-icp-a5-boot.c.proposed').read_text();a=s.rindex('static bool has_ipe_sid_group(');b=s.index('\nstatic int free_transfer_memory(',a)
prefix=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
typedef uint32_t u32;
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
struct device_node{int refs;};struct device{struct device_node *of_node;};
struct of_phandle_args{struct device_node *np;unsigned args_count,args[2];};
static struct device_node nodes[2];static int count,fail_index,wrong_provider,wrong_count,wrong_sid,wrong_mask;
static const u32 pairs[][2]={{0x2222,0},{0x2080,0x20},{0x20a0,0x20},{0x2100,0x20},{0x2120,0x20},{0x20c0,0},{0x2140,0}};
static int of_count_phandle_with_args(struct device_node *n,const char*a,const char*b){(void)n;(void)a;(void)b;return count;}
static int of_parse_phandle_with_args(struct device_node*n,const char*a,const char*b,unsigned i,struct of_phandle_args *out){
 (void)n;(void)a;(void)b;if((int)i==fail_index)return -1;out->np=&nodes[(int)i==wrong_provider];out->np->refs++;out->args_count=(int)i==wrong_count?1:2;out->args[0]=pairs[i][0]^((int)i==wrong_sid?1:0);out->args[1]=pairs[i][1]^((int)i==wrong_mask?1:0);return 0;
}
static struct device_node *of_node_get(struct device_node *n){if(n)n->refs++;return n;}
static void of_node_put(struct device_node*n){if(n){assert(n->refs>0);n->refs--;}}
'''
main=r'''
int main(void){struct device d={0};unsigned cases=0;for(int mode=0;mode<6;mode++)for(int index=0;index<7;index++){
 count=7;fail_index=wrong_provider=wrong_count=wrong_sid=wrong_mask=-1;
 if(mode==1)fail_index=index;if(mode==2)wrong_provider=index;if(mode==3)wrong_count=index;if(mode==4)wrong_sid=index;if(mode==5)wrong_mask=index;
 assert(has_ipe_sid_group(&d)==(mode==0));assert(!nodes[0].refs && !nodes[1].refs);cases++;
}for(int n=-1;n<=8;n++)if(n!=7){count=n;assert(!has_ipe_sid_group(&d));cases++;}printf("SID_CASES %u\n",cases);return 0;}
'''
(work/'probe.c').write_text(prefix+s[a:b]+main)
q=subprocess.run(['cc','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-fsanitize=address,undefined',str(work/'probe.c'),'-o',str(work/'probe')],capture_output=True);assert not q.returncode,q.stderr.decode()
q=subprocess.run([str(work/'probe')],capture_output=True);assert not q.returncode,q.stderr.decode();assert q.stdout==b'SID_CASES 51\n';(work/'result-private.log').write_bytes(q.stdout+q.stderr)
report=dict(stage=381,actual_engine_sid_gate_body=True,tests=51,asan_ubsan=True,missing_malformed_foreign_or_wrong_specs_rejected=True,failed_parse_cannot_keep_previous_success=True,all_of_node_references_balanced=True,iommu_framework_provider_modelled=True,hardware_attachment_not_proven=True,passed=True)
(HERE/'ipe-sids-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
