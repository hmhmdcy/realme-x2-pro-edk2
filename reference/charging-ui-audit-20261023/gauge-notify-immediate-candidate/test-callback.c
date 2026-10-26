/* Actual strict board gate and callback; fake OF and workqueue request boundary. */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>

#define BQ28Z610 28
#define HZ 100
struct device_node { bool compatible; };
struct device { struct device_node *of_node; };
struct delayed_work { bool pending, running; unsigned long due; unsigned int calls; };
struct bq27xxx_device_info { int chip; struct device *dev; struct delayed_work work; int sentinel; };
struct power_supply { struct bq27xxx_device_info *di; };
static bool samurai_instant_current, native_machine;
static unsigned long now;
static int system_percpu_wq;
static struct delayed_work *last_work;
static bool of_machine_is_compatible(const char *name)
{ assert(!strcmp(name, "realme,samurai")); return native_machine; }
static bool of_device_is_compatible(const struct device_node *node, const char *name)
{ assert(!strcmp(name, "ti,bq28z610")); return node && node->compatible; }
static struct bq27xxx_device_info *power_supply_get_drvdata(struct power_supply *psy)
{ return psy->di; }
/* Only the request boundary is modeled. These cases do not run Linux's scheduler. */
static bool mod_delayed_work(int queue, struct delayed_work *work, unsigned long delay)
{
 bool was_pending = work->pending;
 assert(queue == system_percpu_wq);
 last_work = work; work->calls++; work->pending = true; work->due = now + delay;
 return was_pending;
}

#include "actual-functions.inc"

int main(void)
{
 struct device_node node = {true}; struct device dev = {&node};
 struct bq27xxx_device_info di = { .chip = BQ28Z610, .dev = &dev, .sentinel = 1234 };
 struct power_supply psy = {&di};
 native_machine = true; samurai_instant_current = false;
 bq27xxx_external_power_changed(&psy); assert(di.work.due == HZ/2);
 puts("ok: exact native chip opt-out retains half-second delay");
 samurai_instant_current = true;
 bq27xxx_external_power_changed(&psy); assert(di.work.due == 0);
 puts("ok: strict enabled Samurai BQ28 gate requests immediate original work");
 di.chip = BQ28Z610 + 1; bq27xxx_external_power_changed(&psy); assert(di.work.due == HZ/2);
 di.chip = BQ28Z610; native_machine = false; bq27xxx_external_power_changed(&psy); assert(di.work.due == HZ/2);
 native_machine = true; node.compatible = false; bq27xxx_external_power_changed(&psy); assert(di.work.due == HZ/2);
 dev.of_node = NULL; bq27xxx_external_power_changed(&psy); assert(di.work.due == HZ/2);
 dev.of_node = &node; node.compatible = true;
 puts("ok: foreign chip machine node and missing node retain original delay despite global opt-in");
 now = 100; di.work.pending = true; di.work.due = now + 360*HZ;
 bq27xxx_external_power_changed(&psy);
 assert(last_work == &di.work && di.work.pending && di.work.due == now);
 puts("ok: pending 360-second fallback is advanced on the same work item");
 unsigned int calls = di.work.calls;
 for (unsigned int i=0; i<4; i++) { now += 10; bq27xxx_external_power_changed(&psy); assert(di.work.due == now); }
 assert(di.work.calls == calls + 4 && last_work == &di.work && di.sentinel == 1234);
 puts("ok: repeated native notifications never request a new half-second settling interval");
 di.work.pending = false; di.work.running = true; now += 7;
 bq27xxx_external_power_changed(&psy);
 assert(di.work.running && di.work.pending && di.work.due == now && last_work == &di.work);
 puts("ok: running original work receives immediate requeue request without cancellation");
 samurai_instant_current = false; now += 10; bq27xxx_external_power_changed(&psy); assert(di.work.due == now + HZ/2);
 now += 10; bq27xxx_external_power_changed(&psy); assert(di.work.due == now + HZ/2);
 assert(di.sentinel == 1234);
 puts("ok: original profile pending running and repeated delay semantics are unchanged");
 return 0;
}
