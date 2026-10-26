/* Exercise the actual maintained 17x vfe_enable() with a retired PIX RUP. */
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#define CAMSS_8150 8150
#define spin_lock_irqsave(p,f) do { (void)(p); (f)=0; assert(!locked); locked=1; } while(0)
#define spin_unlock_irqrestore(p,f) do { (void)(p); (void)(f); assert(locked); locked=0; } while(0)
#define mutex_lock(p) ((void)(p))
#define mutex_unlock(p) ((void)(p))
struct vfe_line;struct vfe_device;
struct hw_ops { int (*vfe_line_prepare)(struct vfe_line *); void (*reg_update_clear)(struct vfe_device *,int); };
struct resource { struct hw_ops *hw_ops;int version; };
struct camss { struct resource *res; };
struct vfe_device { struct resource *res;struct camss *camss;int stream_lock,output_lock,stream_count,was_streaming;unsigned reg_update;bool ds4,gtm; };
struct vfe_line { struct vfe_device *vfe;bool is_pix;int id; };
static int locked,prepared,applied,enabled,stopped,put,cleared,fail_prepare,fail_enable;
static struct vfe_device *to_vfe(struct vfe_line *l) { return l->vfe; }
static void vfe_enable_irq_common(struct vfe_device *v) { (void)v; }
static int vfe_get_output_v2(struct vfe_line *l) { (void)l;return 0; }
static int prepare(struct vfe_line *l) { prepared++;l->vfe->ds4=false;l->vfe->gtm=false;return fail_prepare; }
static void clear(struct vfe_device *v,int id) { assert(locked&&id==3);v->reg_update&=~1u;cleared++; }
static void vfe_params_apply_queued(struct vfe_device *v,struct vfe_line *l)
{ assert(!locked&&l->is_pix&&prepared);if(v->reg_update&1)return;v->ds4=v->gtm=true;applied++; }
static int vfe_enable_output_v2(struct vfe_line *l)
{ assert(!locked);enabled++;if(l->is_pix)assert(l->vfe->ds4&&l->vfe->gtm);return fail_enable; }
static void vfe_175_pixel_stop(struct vfe_device *v) { stopped++;v->gtm=false; }
static void vfe_put_output(struct vfe_line *l) { (void)l;put++; }
#include "enable-body-private.c"
int main(void)
{
 struct hw_ops ops={prepare,clear};struct resource r={&ops,CAMSS_8150};struct camss c={&r};struct vfe_device v={.res=&r,.camss=&c,.reg_update=9};struct vfe_line l={&v,true,3};
 assert(!vfe_enable(&l));assert(v.reg_update==8&&v.ds4&&v.gtm&&cleared==1&&applied==1&&v.stream_count==1&&v.was_streaming);
 /* Stop/reopen without reloading the module: only the PIX bit is retired. */
 v.reg_update=13;v.stream_count=0;v.was_streaming=0;
 assert(!vfe_enable(&l));assert(v.reg_update==12&&cleared==2&&applied==2&&enabled==2);
 v.stream_count=0;fail_prepare=-22;assert(vfe_enable(&l)==-22);assert(v.stream_count==0&&stopped==1&&put==1&&cleared==2);
 fail_prepare=0;fail_enable=-61;v.reg_update|=1;assert(vfe_enable(&l)==-61);assert(v.stream_count==0&&stopped==2&&put==2&&cleared==3);
 /* Existing non-PIX path neither clears PIX nor consumes PIX parameters. */
 fail_enable=0;l.is_pix=false;v.reg_update=9;assert(!vfe_enable(&l));assert(v.reg_update==9&&cleared==3&&applied==3&&!locked);
 puts("REOPEN_PASS retired_pix_before_params=1 rdi_preserved=1 error_cleanup=1");
}
