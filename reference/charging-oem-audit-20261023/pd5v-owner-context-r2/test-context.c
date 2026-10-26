#include "kernel-boundary-fixture.inc"

struct context_stats {
 int gets,puts,joins,join_exited,destroyed,fail_get_after;
 bool release_in_join,require_join_before_destroy;
};
struct real_context {
 int refs;
 struct context_stats *stats;
 struct samurai_pd5v *owner;
 struct samurai_pd5v_lease lease;
};
static struct real_context *interleaved;
static struct mutex *interleave_lock;
static void context_unlock_hook(struct mutex *m) {
 if(interleaved && m==interleave_lock) {
  struct real_context *ctx=interleaved;
  interleaved=NULL;interleave_lock=NULL;
  /* Model the release thread running after quiesce unlocked, before join. */
  samurai_pd5v_release(&ctx->lease);
 }
}
static bool context_get_unless_zero(void *data) {
 struct real_context *ctx=data;struct context_stats *s=ctx->stats;
 assert(ctx->refs>0 && !s->destroyed && ctx->owner->lock.held);
 s->gets++;
 if(s->fail_get_after && s->gets>=s->fail_get_after)return false;
 ctx->refs++;return true;
}
static void context_put(void *data) {
 struct real_context *ctx=data;struct context_stats *s=ctx->stats;
 assert(ctx->refs>0 && !s->destroyed && !ctx->owner->lock.held && !pd5v_registry_lock.held);
 s->puts++;
 if(!--ctx->refs) {
  if(s->require_join_before_destroy)assert(s->join_exited);
  s->destroyed++;free(ctx);
 }
}
static void context_cancel_join(void *data) {
 struct real_context *ctx=data;struct context_stats *s=ctx->stats;
 assert(ctx->refs>0 && !s->destroyed && !ctx->owner->lock.held && !pd5v_registry_lock.held);
 s->joins++;
 if(s->release_in_join)samurai_pd5v_release(&ctx->lease);
 /* In callback-release case only the quiesce pin keeps this heap object
  * alive here. ASan would detect any borrowed, already freed context. */
 assert(ctx->refs>0 && !s->destroyed);
 s->join_exited++;
}
static struct samurai_pd5v *owner(void) {
 struct samurai_pd5v *p=samurai_pd5v_create(&device,&map);
 assert(!IS_ERR(p));return p;
}
static struct real_context *context(struct samurai_pd5v *p,struct context_stats *s) {
 struct real_context *ctx=calloc(1,sizeof(*ctx));assert(ctx);
 ctx->refs=1;ctx->owner=p;ctx->stats=s;return ctx;
}
static struct samurai_pd5v_client ops(struct real_context *ctx) {
 return (struct samurai_pd5v_client){.context=ctx,.get_unless_zero=context_get_unless_zero,.put=context_put,.cancel_join=context_cancel_join};
}
static void check_ended(void) {
 assert(!module_refs && !pd5v_bound && !device.refs && !rail.refs);
 assert(!interleaved && !interleave_lock);
}
static void mandatory_operations(void) {
 reset();struct samurai_pd5v *p=owner();struct context_stats s={0};struct real_context *ctx=context(p,&s);
 struct samurai_pd5v_client c=ops(ctx),bad=c;
 bad.get_unless_zero=NULL;assert(qcom_pmic_typec_5v_acquire(&device,&bad,&ctx->lease)==-EINVAL);
 bad=c;bad.put=NULL;assert(qcom_pmic_typec_5v_acquire(&device,&bad,&ctx->lease)==-EINVAL);
 bad=c;bad.cancel_join=NULL;assert(qcom_pmic_typec_5v_acquire(&device,&bad,&ctx->lease)==-EINVAL);
 assert(!reads && !writes && !rail.refs && !s.gets && !s.puts && !module_refs);
 context_put(ctx);assert(s.destroyed==1);samurai_pd5v_destroy(p);check_ended();
}
static void acquire_pin_and_io_failure(void) {
 reset();struct samurai_pd5v *p=owner();struct context_stats s={.fail_get_after=1};struct real_context *ctx=context(p,&s);
 struct samurai_pd5v_client c=ops(ctx);
 assert(qcom_pmic_typec_5v_acquire(&device,&c,&ctx->lease)==-ENODEV);
 assert(s.gets==1 && !s.puts && ctx->refs==1 && !reads && !writes && !rail.refs && !module_refs);
 context_put(ctx);samurai_pd5v_destroy(p);check_ended();
 reset();p=owner();s=(struct context_stats){0};ctx=context(p,&s);c=ops(ctx);fail_read_at=1;
 assert(qcom_pmic_typec_5v_acquire(&device,&c,&ctx->lease)==-EREMOTEIO);
 assert(s.gets==1 && s.puts==1 && ctx->refs==1 && !s.destroyed && !module_refs && !writes);
 context_put(ctx);assert(s.destroyed==1);samurai_pd5v_destroy(p);check_ended();
}
static void ordinary_release_destroys_embedded_lease(void) {
 reset();struct samurai_pd5v *p=owner();struct context_stats s={0};struct real_context *ctx=context(p,&s);
 struct samurai_pd5v_client c=ops(ctx);assert(!qcom_pmic_typec_5v_acquire(&device,&c,&ctx->lease));
 assert(ctx->refs==2 && s.gets==1 && !s.puts);context_put(ctx);assert(ctx->refs==1);
 samurai_pd5v_release(&ctx->lease); /* Frees ctx AND this lease before returning. */
 assert(s.destroyed==1 && s.puts==2 && !module_refs && !p->leased);
 samurai_pd5v_destroy(p);check_ended();
}
static void release_between_pin_and_join(void) {
 reset();struct samurai_pd5v *p=owner();struct context_stats s={.release_in_join=true,.require_join_before_destroy=true};struct real_context *ctx=context(p,&s);
 struct samurai_pd5v_client c=ops(ctx);assert(!qcom_pmic_typec_5v_acquire(&device,&c,&ctx->lease));context_put(ctx);
 interleaved=ctx;interleave_lock=&p->lock;
 assert(!samurai_pd5v_quiesce(p));
 assert(s.gets==2 && s.puts==3 && s.joins==1 && s.join_exited==1 && s.destroyed==1);
 assert(!p->leased && !module_refs);samurai_pd5v_destroy(p);check_ended();
}
static void callback_releases_without_deadlock(void) {
 reset();struct samurai_pd5v *p=owner();struct context_stats s={.release_in_join=true,.require_join_before_destroy=true};struct real_context *ctx=context(p,&s);
 struct samurai_pd5v_client c=ops(ctx);assert(!qcom_pmic_typec_5v_acquire(&device,&c,&ctx->lease));context_put(ctx);
 assert(!samurai_pd5v_quiesce(p));
 assert(s.gets==2 && s.puts==3 && s.joins==1 && s.destroyed==1 && !module_refs);
 samurai_pd5v_destroy(p);check_ended();
}
static void failed_extra_pin_blocks_PM(void) {
 reset();struct samurai_pd5v *p=owner();struct context_stats s={.fail_get_after=2};struct real_context *ctx=context(p,&s);
 struct samurai_pd5v_client c=ops(ctx);assert(!qcom_pmic_typec_5v_acquire(&device,&c,&ctx->lease));context_put(ctx);
 struct pmic_typec t={.pd5v=p};device.driverdata=&t;
 int old_reads=reads,old_writes=writes;
 assert(qcom_pmic_typec_prepare(&device)==-EOWNERDEAD);
 assert(p->error==-EOWNERDEAD && p->blocked && p->leased && ctx->refs==1 && !s.joins && s.puts==1);
 assert(samurai_pd5v_validate(&ctx->lease)==-ESTALE);
 qcom_pmic_typec_complete(&device);assert(p->blocked && reads==old_reads && writes==old_writes);
 samurai_pd5v_release(&ctx->lease);assert(s.destroyed==1 && !module_refs);
 device.driverdata=NULL;samurai_pd5v_destroy(p);check_ended();
}
static void failed_extra_pin_remove_retains_binding_until_release(void) {
 reset();struct samurai_pd5v *p=owner();struct context_stats s={.fail_get_after=2};struct real_context *ctx=context(p,&s);
 struct samurai_pd5v_client c=ops(ctx);assert(!qcom_pmic_typec_5v_acquire(&device,&c,&ctx->lease));context_put(ctx);
 int old_reads=reads,old_writes=writes;
 samurai_pd5v_destroy(p);
 assert(pd5v_bound==p && p->removed && p->leased && p->error==-EOWNERDEAD);
 assert(p->ref.refs==2 && rail.refs==1 && device.refs==1 && module_refs==1 && !s.joins && !s.destroyed);
 struct samurai_pd5v *replacement=samurai_pd5v_create(&device,&map);
 assert(IS_ERR(replacement) && PTR_ERR(replacement)==-EBUSY);
 struct samurai_pd5v_lease denied={0};
 assert(qcom_pmic_typec_5v_acquire(&device,&c,&denied)==-EOWNERDEAD);
 assert(reads==old_reads && writes==old_writes && s.gets==2);
 samurai_pd5v_release(&ctx->lease);
 assert(s.destroyed==1 && !pd5v_bound && !module_refs && !device.refs && !rail.refs);
 check_ended();
}
static void pinned_but_join_failed_retains_primary_reference(void) {
 reset();struct samurai_pd5v *p=owner();struct context_stats s={0};struct real_context *ctx=context(p,&s);
 struct samurai_pd5v_client c=ops(ctx);assert(!qcom_pmic_typec_5v_acquire(&device,&c,&ctx->lease));context_put(ctx);
 assert(samurai_pd5v_quiesce(p)==-EBUSY);
 assert(s.gets==2 && s.puts==2 && s.joins==1 && !s.destroyed && ctx->refs==1 && p->leased);
 samurai_pd5v_release(&ctx->lease);assert(s.destroyed==1);samurai_pd5v_destroy(p);check_ended();
}
int main(void) {
 mandatory_operations();acquire_pin_and_io_failure();ordinary_release_destroys_embedded_lease();
 release_between_pin_and_join();callback_releases_without_deadlock();failed_extra_pin_blocks_PM();
 failed_extra_pin_remove_retains_binding_until_release();pinned_but_join_failed_retains_primary_reference();
 puts("PASS: 8 affected context-lifetime groups; no original seven groups executed");return 0;
}
