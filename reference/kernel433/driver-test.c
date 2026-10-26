/* SPDX-License-Identifier: GPL-2.0-only */
/* Execute actual GTM, queue, RUP and SOF functions with bounded MMIO/IRQ fixtures. */
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <linux/qcom-camss-config.h>
typedef uint64_t u64;
typedef uint32_t u32;
typedef uint16_t u16;
typedef uint8_t u8;
#define BIT(n) (1u << (n))
#define GENMASK(h,l) ((~0u << (l)) & (~0u >> (31-(h))))
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define container_of(p,t,m) ((t *)((char *)(p)-offsetof(t,m)))
#define WARN_ON_ONCE(x) ({ bool bad=(x);assert(!bad);bad; })
#define WARN_ON(x) WARN_ON_ONCE(x)
#define IS_ERR(p) ((uintptr_t)(p) >= (uintptr_t)-4095)
#define ERR_PTR(n) ((void *)(intptr_t)(n))
#define dev_err(...) ((void)0)
#define CAMSS_8150 8150
#define VFE_OUTPUT_ON 1
#define CAMSS_INIT_BUF_COUNT 2
#define REG_UPDATE_RDI(n) BIT(1+(n))
#define VFE_REG_UPDATE_CMD 0x4ac
#define VB2_BUF_STATE_DONE 1
enum vfe_line_id { VFE_LINE_RDI0, VFE_LINE_RDI1, VFE_LINE_RDI2, VFE_LINE_PIX };
#include "camss-vfe-175-gtm.h"
struct device { int unused; };
struct vfe_device;
struct vfe_line;
struct vb2_buffer { u64 timestamp; unsigned done; };
struct camss_buffer {
	struct { struct vb2_buffer vb2_buf; u32 sequence; } vb;
	bool sof_valid;
	u64 gtm_cookie,gtm_generation;
	u32 gtm_status,gtm_bank;
	void *meta;
	struct camss_buffer *next;
};
struct queue { struct camss_buffer *head,*tail; };
struct vfe_output {
	int state,wm_num,wait_reg_update,reg_update;
	u32 sof_sequence;
	struct queue pending_bufs;
	struct camss_buffer *buf[2];
	size_t stats_payload_size;
};
struct vfe_line { bool is_pix;struct vfe_output output[4];unsigned num_outputs;int subdev; };
struct vfe_hw_ops {
	void (*vfe_params_apply)(struct vfe_device *,struct vfe_line *,const struct v4l2_isp_buffer *);
	void (*reg_update)(struct vfe_device *,enum vfe_line_id);
	void (*reg_update_clear)(struct vfe_device *,enum vfe_line_id);
};
struct camss_res { int version; };
struct camss { struct device *dev;struct camss_res *res; };
struct vfe_res { const struct vfe_hw_ops *hw_ops; };
struct vfe_device {
	void *base;struct camss *camss;struct vfe_res *res;
	struct { struct vfe_175_gtm_state gtm; } pixel175;
	u32 reg_update;
	int output_lock;
	struct vfe_line line[4];
};
struct v4l2_isp_stats_block_type_info { size_t size; };
static unsigned lock_depth,writes,barriers,dmi_count,oracle_count,notifies;
struct event { u32 address,value; };
static struct event dmi_trace[128],oracle_trace[128];
static u32 memory[1024],lo_latch;
static u64 ram[2][64];
static bool lo_valid;
static unsigned port(const void *p)
{
	ptrdiff_t off=(const char *)p-(const char *)memory;
	assert(off>=0&&(size_t)off<sizeof(memory)&&off%4==0);return off;
}
static u32 readl_relaxed(const void *p) { return memory[port(p)/4]; }
#define readl readl_relaxed
static void writel_relaxed(u32 value,void *p)
{
	unsigned off=port(p);writes++;
	if(off==0xc30||off==0xc2c) {
		assert(dmi_count<128);dmi_trace[dmi_count++]=(struct event){off,value};
		unsigned selector=memory[0xc24/4]&127,index=memory[0xc28/4];
		assert(selector==24||selector==25);assert(index<64);assert(memory[0x34/4]&4);
		assert(!(memory[0xc24/4]&(BIT(8)|BIT(12))));
		assert((selector-24)!=(memory[0x794/4]&1));
		if(off==0xc30){assert(!lo_valid);lo_latch=value;lo_valid=true;}
		else {assert(lo_valid);ram[selector-24][index]=((u64)value<<32)|lo_latch;lo_valid=false;}
	}
	if(off==0x794)assert(dmi_count==128&&!lo_valid);
	memory[off/4]=value;
}
#define writel writel_relaxed
#define wmb() do {barriers++;} while(0)
#define spin_lock_irqsave(lock,flags) do {(void)(lock);(flags)=0;assert(lock_depth++==0);}while(0)
#define spin_unlock_irqrestore(lock,flags) do {(void)(lock);(void)(flags);assert(lock_depth--==1);}while(0)
static void complete(int *value) { (*value)++; }
static u64 ktime_get_ns(void) { static u64 t=100;return ++t; }
static void vb2_buffer_done(struct vb2_buffer *buf,int state)
{ assert(!lock_depth&&state==VB2_BUF_STATE_DONE);buf->done++; }
static void v4l2_subdev_notify_event(int *subdev,const struct v4l2_event *event)
{ (void)subdev;assert(!lock_depth&&event->type==V4L2_EVENT_FRAME_SYNC);notifies++; }
#define list_first_entry_or_null(q,type,member) ((q)->head)
static struct vfe_output *vfe_params_output(struct vfe_line *line) { return &line->output[1]; }
static struct camss_buffer *vfe_buf_get_pending(struct vfe_output *output)
{
	struct camss_buffer *b=output->pending_bufs.head;
	if(b){output->pending_bufs.head=b->next;if(!b->next)output->pending_bufs.tail=NULL;}return b;
}
static void enqueue(struct vfe_output *output,struct camss_buffer *buf)
{
	buf->next=NULL;
	if(output->pending_bufs.tail)output->pending_bufs.tail->next=buf;else output->pending_bufs.head=buf;
	output->pending_bufs.tail=buf;
}
#include "stats-functions-private.c"
#include "gtm-driver-body-private.c"
static void apply(struct vfe_device *vfe,struct vfe_line *line,const struct v4l2_isp_buffer *params)
{ (void)line;assert(params->data_size==sizeof(struct camss_params_ife_gtm));vfe_175_gtm_params(vfe,(const void *)params->data); }
#include "integration-functions-private.c"
#define CAM_CDM_CMD_SWD_DMI_64 0x71
#define CAM_CDM_DMI_DATA_LO_OFFSET 12
#define CAM_CDM_DMI_DATA_HI_OFFSET 8
#define CAM_ERR(...) ((void)0)
#define __iomem
static unsigned cdm_required_size_dmi(void) { return 3; }
static void cam_io_w_mb(u32 value,void *p)
{ assert(oracle_count<128);oracle_trace[oracle_count++]=(struct event){port(p),value}; }
#include "official-cdm-functions-private.c"
static void reset_mmio(unsigned bank)
{
	for(unsigned i=0;i<1024;i++)memory[i]=0xa5a50000u+i;
	memory[0x794/4]=(memory[0x794/4]&~1u)|bank;
	memory[0x34/4]&=~4u;memory[0xc24/4]=0xa50011c1;
	memset(ram,0xa7,sizeof(ram));lo_valid=false;dmi_count=writes=barriers=0;
}
static struct v4l2_isp_buffer *packet(u64 *storage,const struct camss_params_ife_gtm *gtm,unsigned copies)
{
	struct v4l2_isp_buffer *p=(void *)storage;p->version=1;p->data_size=sizeof(*gtm)*copies;
	for(unsigned i=0;i<copies;i++)memcpy(p->data+i*sizeof(*gtm),gtm,sizeof(*gtm));return p;
}
static void done_buffer(struct vfe_device *vfe,struct camss_buffer *p)
{
	unsigned long flags;spin_lock_irqsave(&vfe->output_lock,flags);
	struct camss_buffer *got=vfe_params_apply_next(vfe,&vfe->line[3],99);
	spin_unlock_irqrestore(&vfe->output_lock,flags);assert(got==p);
}
int main(int argc,char **argv)
{
	assert(argc==2&&sizeof(struct camss_params_ife_gtm)==536&&sizeof(struct camss_stats_ife_gtm)==32);
	FILE *f=fopen(argv[1],"rb");assert(f);u32 native[128];assert(fread(native,sizeof(native),1,f)==1);assert(fgetc(f)==EOF);fclose(f);
	struct camss_params_ife_gtm gtm={.header={CAMSS_PARAMS_IFE_GTM,0,sizeof(gtm)},.cookie=UINT64_C(0x1122334455667788),.enabled=1};
	for(unsigned i=0;i<64;i++){gtm.segments[i].base=native[i*2];u32 s=native[i*2+1];gtm.segments[i].slope=(s&BIT(25))?(int64_t)s-(INT64_C(1)<<26):s;}
	u32 packed[128];assert(!vfe_175_gtm_validate(NULL,&gtm.header));assert(!vfe_175_gtm_encode(&gtm,packed));assert(!memcmp(packed,native,sizeof(native)));
	for(unsigned i=0;i<64;i++)for(unsigned bad=0;bad<3;bad++){
		struct camss_params_ife_gtm invalid=gtm;
		if(!bad)invalid.segments[i].base=0x40000;else invalid.segments[i].slope=bad==1?-(1<<25)-1:(1<<25);
		memset(packed,0xa7,sizeof(packed));assert(vfe_175_gtm_encode(&invalid,packed)==-EINVAL);for(unsigned j=0;j<128;j++)assert(packed[j]==0xa7a7a7a7);
	}
	for(unsigned flags=1;flags<8;flags++){gtm.header.flags=flags;assert(vfe_175_gtm_validate(NULL,&gtm.header)==-EINVAL);}gtm.header.flags=0;
	gtm.header.size=8;assert(vfe_175_gtm_validate(NULL,&gtm.header)==-EINVAL);gtm.header.size=sizeof(gtm);
	struct device device={0};struct camss_res cres={CAMSS_8150};struct camss camss={&device,&cres};
	struct vfe_hw_ops ops={apply,vfe_reg_update,vfe_reg_update_clear};struct vfe_res res={&ops};struct vfe_device vfe={.base=memory,.camss=&camss,.res=&res};
	struct vfe_line *line=&vfe.line[3];line->is_pix=true;line->num_outputs=4;
	for(unsigned i=0;i<4;i++){line->output[i].state=VFE_OUTPUT_ON;line->output[i].wm_num=i==1?0:1;line->output[i].stats_payload_size=CAMSS_STATS_MAX_PAYLOAD;}
	u64 pa[140]={0},pb[140]={0};struct camss_buffer a={.meta=packet(pa,&gtm,1)};
	assert(!vfe_175_gtm_validate_buffer(a.meta));packet(pb,&gtm,2);assert(vfe_175_gtm_validate_buffer((void *)pb)==-EINVAL);
	reset_mmio(0);u32 saved_dmi=memory[0xc24/4],saved_address=memory[0xc28/4],saved_cgc=memory[0x34/4],saved_cfg=memory[0x794/4],saved_enable=memory[0x48/4];
	enqueue(&line->output[1],&a);vfe.reg_update=1;done_buffer(&vfe,NULL);assert(!writes&&vfe.pixel175.gtm.deferred);
	vfe_isr_reg_update(&vfe,VFE_LINE_PIX);assert(a.vb.vb2_buf.done==1&&vfe.pixel175.gtm.pending&&vfe.pixel175.gtm.armed);
	assert(!vfe.pixel175.gtm.cookie&&dmi_count==128&&vfe.reg_update==1);
	assert(memory[0xc24/4]==saved_dmi&&memory[0xc28/4]==saved_address&&memory[0x34/4]==saved_cgc&&memory[0x794/4]==(saved_cfg^1));
	assert(memory[0x48/4]==(saved_enable|4));assert(!memcmp(ram[1],native,512));for(unsigned i=0;i<64;i++)assert(ram[0][i]==UINT64_C(0xa7a7a7a7a7a7a7a7));
	u32 command[131]={511,0,0xc24};memcpy(command+3,native,512);u32 used=0;assert(!cam_cdm_util_swd_dmi_write(CAM_CDM_CMD_SWD_DMI_64,memory,command,sizeof(command),&used));assert(used==524&&oracle_count==128&&!memcmp(oracle_trace,dmi_trace,sizeof(dmi_trace)));
	struct camss_buffer before={0};line->output[2].buf[0]=&before;vfe_isr_sof(&vfe,VFE_LINE_PIX);assert(before.sof_valid&&!before.gtm_cookie);
	/* An unarmed stale ACK cannot publish a newly written state. */
	vfe.pixel175.gtm.armed=false;vfe_175_gtm_ack(&vfe);assert(!vfe.pixel175.gtm.cookie);vfe.pixel175.gtm.armed=true;
	gtm.cookie++;struct camss_buffer b={.meta=packet(pb,&gtm,1)};enqueue(&line->output[1],&b);done_buffer(&vfe,NULL);dmi_count=0;
	vfe_isr_reg_update(&vfe,VFE_LINE_PIX);assert(vfe.pixel175.gtm.cookie==gtm.cookie-1&&vfe.pixel175.gtm.generation==1&&vfe.pixel175.gtm.pending&&b.vb.vb2_buf.done==1);
	struct camss_buffer captured={0};line->output[2].buf[0]=&captured;vfe_isr_sof(&vfe,VFE_LINE_PIX);assert(captured.gtm_cookie==gtm.cookie-1&&captured.gtm_generation==1&&captured.gtm_bank==1);
	vfe_isr_reg_update(&vfe,VFE_LINE_PIX);assert(vfe.pixel175.gtm.cookie==gtm.cookie&&vfe.pixel175.gtm.generation==2&&!vfe.pixel175.gtm.pending);
	u64 stats_memory[16]={0};struct v4l2_isp_buffer *stats=(void *)stats_memory;vfe_175_gtm_fill(&vfe,&line->output[2],&captured,stats);
	struct camss_stats_ife_gtm *receipt=(void *)stats->data;assert(stats->data_size==32&&receipt->cookie==captured.gtm_cookie&&receipt->generation==1&&receipt->status==3&&receipt->bank==1);
	gtm.cookie++;gtm.enabled=0;packet(pa,&gtm,1);a.vb.vb2_buf.done=0;enqueue(&line->output[1],&a);unsigned prior=writes;
	done_buffer(&vfe,&a);assert(writes==prior+1&&vfe.pixel175.gtm.cookie==gtm.cookie-1);vfe_reg_update(&vfe,VFE_LINE_PIX);vfe_isr_reg_update(&vfe,VFE_LINE_PIX);
	assert(vfe.pixel175.gtm.cookie==gtm.cookie&&vfe.pixel175.gtm.generation==3&&vfe.pixel175.gtm.status==1);
	vfe_175_gtm_stop(&vfe);vfe_isr_reg_update(&vfe,VFE_LINE_PIX);assert(!vfe.pixel175.gtm.cookie&&!vfe.pixel175.gtm.pending&&!vfe.pixel175.gtm.tracking);
	assert(!lock_depth&&notifies==2);printf("GTM_DRIVER_PASS rejection_cases=200 old_ack_deferred=1 delayed_snapshot=1 stop_restart=1 dmi64_gpl_oracle=1\n");return 0;
}
