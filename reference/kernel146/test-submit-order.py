"""Compile the actual submit function with packet recording stubs."""
from pathlib import Path
import json
import subprocess

out = Path('/mnt/e/edk2-samurai-out/kernel146')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel146')
stub = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stddef.h>
typedef uint32_t u32;
struct packet { int type, op, len; uint64_t data[8]; };
static struct packet packets[256];
static int np, data_idx;
struct msm_ringbuffer { unsigned int cur_ctx_seqno; };
struct msm_gpu { int model; };
struct gpu_funcs { uint64_t (*get_timestamp)(struct msm_gpu *); };
struct adreno_gpu { struct gpu_funcs *funcs; };
struct a6xx_gpu { int dummy; };
struct ctx { unsigned int seqno; };
struct queue { struct ctx *ctx; };
struct cmd { int type; uint64_t iova; unsigned int size; };
struct msm_gem_submit { unsigned int seqno, nr_cmds; struct msm_ringbuffer *ring; struct queue *queue; struct cmd cmd[40]; };
enum { MSM_SUBMIT_CMD_IB_TARGET_BUF, MSM_SUBMIT_CMD_CTX_RESTORE_BUF, MSM_SUBMIT_CMD_BUF };
enum { CP_EVENT_WRITE=0x46, CP_INDIRECT_BUFFER=0x3f, PC_CCU_INVALIDATE_DEPTH=0x18, PC_CCU_INVALIDATE_COLOR=0x19, CACHE_FLUSH_TS=4, CP_EVENT_WRITE_0_IRQ=0x80000000 };
#define MSM_GPU_SUBMIT_STATS_COUNT 64
#define REG_A6XX_RBBM_PERFCTR_CP(x) 100
#define REG_A6XX_CP_ALWAYS_ON_CONTEXT 101
#define REG_A6XX_CP_SCRATCH(x) 102
#define CP_EVENT_WRITE_0_EVENT(x) (x)
#define A5XX_CP_INDIRECT_BUFFER_2_IB_SIZE(x) (x)
#define lower_32_bits(x) ((uint32_t)(x))
#define upper_32_bits(x) ((uint32_t)((uint64_t)(x)>>32))
#define fallthrough __attribute__((fallthrough))
#define rbmemptr_stats(r,i,f) 0
#define rbmemptr(r,f) 0x1000000001000ULL
static struct adreno_gpu adreno;
static struct a6xx_gpu a6xx;
static int model;
static struct adreno_gpu *to_adreno_gpu(struct msm_gpu *g) { model=g->model; return &adreno; }
static struct a6xx_gpu *to_a6xx_gpu(struct adreno_gpu *g) { return &a6xx; }
static bool adreno_is_a640(struct adreno_gpu *g) { return model==640; }
static void pkt(int type,int op,int n) { packets[np++]=(struct packet){.type=type,.op=op,.len=n}; data_idx=0; }
#define OUT_PKT7(r,op,n) pkt(7,op,n)
#define OUT_PKT4(r,op,n) pkt(4,op,n)
#define OUT_RING(r,v) (packets[np-1].data[data_idx++]=(uint64_t)(v))
static void adreno_check_and_reenable_stall(struct adreno_gpu *g) {}
static void a6xx_set_pagetable(struct a6xx_gpu *g,struct msm_ringbuffer *r,struct msm_gem_submit *s) { if(r->cur_ctx_seqno!=s->queue->ctx->seqno) pkt(99,1,0); }
static void get_stats_counter(struct msm_ringbuffer *r,unsigned int c,uint64_t v) { pkt(99,2,0); }
static void update_shadow_rptr(struct msm_gpu *g,struct msm_ringbuffer *r) { pkt(99,3,0); }
static void a6xx_flush(struct msm_gpu *g,struct msm_ringbuffer *r) { pkt(99,4,0); }
static void trace_msm_gpu_submit_flush(struct msm_gem_submit *s,uint64_t ts) {}
static uint64_t timestamp(struct msm_gpu *g) { return 0; }
'''
main = r'''
int main(void) {
  struct gpu_funcs funcs={.get_timestamp=timestamp}; adreno.funcs=&funcs;
  for(int gpu=0;gpu<2;gpu++) for(int variant=0;variant<5;variant++) {
    struct msm_gpu g={.model=gpu?630:640}; struct msm_ringbuffer r={.cur_ctx_seqno=variant==1?7:0};
    struct ctx ctx={.seqno=7}; struct queue q={.ctx=&ctx};
    struct msm_gem_submit s={.seqno=65,.ring=&r,.queue=&q,.nr_cmds=variant==0?0:variant==4?33:3};
    for(unsigned int i=0;i<s.nr_cmds;i++) s.cmd[i]=(struct cmd){.type=MSM_SUBMIT_CMD_BUF,.iova=0x100000100ULL+i*4096,.size=64};
    if(variant==2) s.cmd[0].type=MSM_SUBMIT_CMD_CTX_RESTORE_BUF;
    if(variant==3) s.cmd[0].type=MSM_SUBMIT_CMD_IB_TARGET_BUF;
    np=0; a6xx_submit(&g,&s);
    int first_ib=-1,last_ib=-1,depth=-1,color=-1,fence=-1,table=-1,ib_count=0;
    for(int i=0;i<np;i++) {
      struct packet *p=&packets[i];
      if(p->type==99 && p->op==1) table=i;
      if(p->type==7 && p->op==CP_INDIRECT_BUFFER) { if(first_ib<0) first_ib=i; last_ib=i; ib_count++; assert(p->len==3 && p->data[2]==64); }
      if(p->type==7 && p->op==CP_EVENT_WRITE) {
        if(p->len==1 && p->data[0]==PC_CCU_INVALIDATE_DEPTH) { assert(depth<0); depth=i; }
        if(p->len==1 && p->data[0]==PC_CCU_INVALIDATE_COLOR) { assert(color<0); color=i; }
        if(p->len==4 && p->data[0]==(CACHE_FLUSH_TS|CP_EVENT_WRITE_0_IRQ)) { fence=i; assert(p->data[3]==65); }
      }
    }
    assert(depth>=0 && color==depth+1 && fence>color);
    assert(table<0 || table<depth);
    assert(ib_count==(variant==0?0:variant==3?2:variant==4?33:3));
    if(first_ib>=0) {
#ifdef CANDIDATE
      if(g.model==640) assert(depth>last_ib); else assert(color<first_ib);
#else
      assert(color<first_ib);
#endif
    }
    assert(packets[np-1].type==99 && packets[np-1].op==4);
    printf("gpu=%d variant=%d packets=%d depth=%d color=%d last_ib=%d fence=%d PASS\n",g.model,variant,np,depth,color,last_ib,fence);
  }
}
'''
results = {}
for label, name in [('baseline','a6xx-before-private.c'),('candidate','a6xx-candidate-private.c')]:
    text = (out / name).read_text()
    start = text.index('static void a6xx_submit(')
    end = text.index('\nvoid a6xx_emit_set_pseudo_reg', start)
    function = text[start:end]
    if label=='candidate':
        hstart=text.index('static void a6xx_invalidate_ccu(')
        function=text[hstart:start]+function
    c=out / (label+'-submit-test-private.c')
    c.write_text(stub+function+main)
    binary=out / (label+'-submit-test-private')
    cmd=['gcc','-std=gnu11','-Werror','-fsanitize=address,undefined','-g',str(c),'-o',str(binary)]
    if label=='candidate': cmd.insert(1,'-DCANDIDATE')
    subprocess.run(cmd,check=True)
    run=subprocess.run([str(binary)],capture_output=True,text=True,check=True)
    (out / (label+'-submit-test-private.log')).write_text(run.stdout+run.stderr)
    results[label]=dict(cases=run.stdout.count('PASS'), returncode=run.returncode)
    assert results[label]['cases']==10
(ref / 'submit-order-test-validation.json').write_text(json.dumps(dict(stage=146,
    actual_submit_function_compiled=True, address_and_undefined_sanitizers=True,
    cases_per_version=10, results=results, hardware_validation_required=True),indent=2)+'\n')
print('K146_ACTUAL_SUBMIT_FUNCTION_BASELINE_AND_CANDIDATE_20_CASES_PASS')
