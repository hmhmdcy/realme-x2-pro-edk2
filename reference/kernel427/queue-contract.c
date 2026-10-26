static struct vfe_device v;
static struct camss c;
static typeof(*c.res) cr;
static typeof(*v.res) vr;
static struct camss_buffer image[8], coarse[8];
static struct vfe_output *im, *ds;
static unsigned starts, stops, dma_addresses, fallback_starts;
static int reject_prepare;
static char order[64];
static unsigned order_count;
static int prepare(struct vfe_device *d, struct vfe_output *o)
{(void)d;(void)o;return reject_prepare;}
static void start(struct vfe_device *d, struct vfe_output *o)
{(void)d;if(o->video_out.auxiliary)assert(o->gen2.active_num);starts++;order[order_count++]='S';}
static void stop(struct vfe_device *d, struct vfe_output *o)
{(void)d;(void)o;stops++;order[order_count++]='T';}
static void fallback_start(struct vfe_device *d,u8 wm,struct vfe_line*l)
{(void)d;(void)wm;(void)l;fallback_starts++;assert(!"Auxiliary image must not run legacy RDI WM start");}
static void address(struct vfe_device *d,struct vfe_output *o,struct camss_buffer *b)
{(void)d;assert(b);updates++;if(o->video_out.auxiliary){assert(starts>stops);dma_addresses++;order[order_count++]='W';}}
static const struct vfe_hw_ops ops={.vfe_output_prepare=prepare,.vfe_output_start=start,.vfe_output_stop=stop,.vfe_wm_start=fallback_start,.vfe_output_update=address,.reg_update=reg_update,.vfe_params_apply=apply};
static void setup(void)
{
 memset(&v,0,sizeof(v));memset(image,0,sizeof(image));memset(coarse,0,sizeof(coarse));
 errors=notifications=updates=reg_updates=applied=stats_filled=locked=starts=stops=dma_addresses=fallback_starts=order_count=reject_prepare=0;
 cr.version=CAMSS_8150;c.res=&cr;vr.hw_ops=&ops;v.res=&vr;v.camss=&c;
 struct vfe_line *l=&v.line[0];l->owner=&v;l->is_pix=true;l->num_outputs=4;
 for(unsigned i=0;i<4;i++)l->output[i].line=l;
 im=&l->output[0];im->wm_num=2;im->state=VFE_OUTPUT_ON;im->comp_group=0;
 l->output[1].pad=MSM_VFE_PAD_SINK_PARAMS;l->output[2].pad=MSM_VFE_PAD_SRC_STATS;
 ds=&l->output[3];ds->wm_num=1;ds->wm[0].bus_client=5;ds->pad=2;ds->comp_group=1;ds->video_out.auxiliary=true;
 im->buf[0]=&image[0];im->buf[1]=&image[1];im->gen2.active_num=2;
}
static void done(unsigned mask){struct camss_buf_done_info info={.status=mask};vfe_buf_done(&v,0,&info);}
static void queue(struct vfe_output *o,struct camss_buffer*b){assert(!vfe_queue_buffer_v2(&o->video_out,b));}
int main(void)
{
 setup();queue(ds,&coarse[0]);queue(ds,&coarse[1]);assert(!starts && !dma_addresses);
 assert(!vfe_enable_one_output(&v.line[0],ds));assert(starts==1 && dma_addresses==2 && !fallback_starts && !memcmp(order,"SWW",3));
 im->sof_sequence=42;vfe_isr_sof(&v,0);done(1);
 assert(image[0].vb.vb2_buf.state==VB2_BUF_STATE_DONE && !coarse[0].vb.vb2_buf.done);
 done(2);assert(coarse[0].vb.sequence==42 && coarse[0].vb.vb2_buf.state==VB2_BUF_STATE_DONE && !stops);
 vfe_isr_sof(&v,0);done(3);assert(image[1].vb.sequence==43 && coarse[1].vb.sequence==43 && stops==1 && !ds->gen2.active_num);
 for(unsigned i=0;i<4;i++)vfe_isr_sof(&v,0);
 queue(ds,&coarse[2]);assert(starts==2 && !memcmp(order+order_count-2,"SW",2));
 vfe_isr_sof(&v,0);done(2);assert(coarse[2].vb.sequence==48 && coarse[2].vb.vb2_buf.state==VB2_BUF_STATE_DONE && stops==2);
 setup();assert(!vfe_enable_one_output(&v.line[0],ds));assert(!starts && !fallback_starts);
 queue(ds,&coarse[0]);assert(starts==1 && dma_addresses==1 && !memcmp(order,"SW",2));
 done(2);assert(coarse[0].vb.vb2_buf.state==VB2_BUF_STATE_ERROR && stops==1);
 setup();queue(ds,&coarse[0]);reject_prepare=-ENODATA;
 assert(vfe_enable_one_output(&v.line[0],ds)==-ENODATA && !starts && !dma_addresses && !ds->state);
 setup();queue(ds,&coarse[0]);assert(!vfe_enable_one_output(&v.line[0],ds));
 ds->state=VFE_OUTPUT_OFF;vfe_isr_sof(&v,0);done(2);assert(!coarse[0].vb.vb2_buf.done);
 puts("DS4_QUEUE_CONTRACTS_PASSED");return 0;
}
