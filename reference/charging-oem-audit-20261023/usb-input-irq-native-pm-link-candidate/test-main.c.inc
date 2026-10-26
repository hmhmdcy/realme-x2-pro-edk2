int main(void)
{
 struct device_node parent_node={0},a,b;
 struct device parent={.of_node=&parent_node};
 struct platform_device p={.dev={.parent=&parent,.registered=true}},c={.dev={.registered=true}};
 unsigned int cases=0;
 /* These old functions are included as exact dependencies, not re-tested. */
 (void)&dwc3_vbus_draw_work;(void)&samurai_usb_suspend;(void)&samurai_usb_resume;
#define SETUP() do { reset();a=(struct device_node){true,"snps,dwc3","samurai-usb-input",0,&c};b=(struct device_node){0};legacy=&a;require_link=true;}while(0)
#define DONE() do { cleanup();check_refs(&a,&b,&c);assert(!link_refs);++cases;}while(0)
 SETUP();assert(!samurai_usb_probe(&p));assert(irq_requests==2&&published&&queued==1);
 assert(allocated->native_consumer==&c.dev&&c.dev.refs==1);DONE();
 assert(!strcmp(order,"LABYSXjiUP")&&irqs_released==2&&link_removes==1);
 SETUP();link_ok=false;assert(samurai_usb_probe(&p)==-EINVAL);assert(!irq_requests&&!published);DONE();
 assert(link_adds==1&&!link_removes);
 SETUP();add_action_fail=1;assert(samurai_usb_probe(&p)==-ENOMEM);assert(!irq_requests&&!published);DONE();
 assert(link_removes==1);
 SETUP();a.pdev=NULL;assert(samurai_usb_probe(&p)==-EPROBE_DEFER);assert(!irq_requests&&!published&&!link_adds);DONE();
 SETUP();irq_failed_at=1;assert(samurai_usb_probe(&p)==-EIO);assert(irq_requests==1&&!published&&!queued);DONE();
 assert(!irqs_released&&!strcmp(order,"LUP"));
 SETUP();irq_failed_at=2;assert(samurai_usb_probe(&p)==-EIO);assert(irq_requests==2&&!published&&!queued);DONE();
 assert(irqs_released==1&&!strcmp(order,"LAiUP"));
 SETUP();publish_ok=false;assert(samurai_usb_probe(&p)==-EIO);assert(irq_requests==2&&!published&&!queued);DONE();
 assert(irqs_released==2&&!strcmp(order,"LABYjiUP"));
 /* This preserves and labels the existing post-publication failure boundary. */
 SETUP();add_action_fail=2;assert(samurai_usb_probe(&p)==-ENOMEM);assert(published&&cancels==1&&!queued);
 DONE();assert(!strcmp(order,"LABYSXjiUP"));
 printf("{\"passed\":true,\"actual_function_cases\":%u,\"actual_merged_probe_and_irq_bodies\":true,\"OF_driver_core_devres_PSY_workqueue_faked\":true}\n",cases);
 return 0;
}
