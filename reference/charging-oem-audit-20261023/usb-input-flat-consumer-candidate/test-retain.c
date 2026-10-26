/* Actual production function; only OF/module/log boundaries are fake. */
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
struct device { int unused; };
struct device_node { bool available, compatible; const char *name; int puts; };
static struct device_node *legacy, *flat;
static bool native_retained;
static int module_gets, logs, legacy_lookups, flat_lookups;
#define THIS_MODULE ((void *)0x1234)
static struct device_node *of_find_node_by_path(const char *name)
{
 if (!strcmp(name,"/soc@0/usb@a6f8800/usb@a600000")) { legacy_lookups++; return legacy; }
 assert(!strcmp(name,"/soc@0/usb@a600000")); flat_lookups++; return flat;
}
static bool of_device_is_available(struct device_node *node) { return node->available; }
static bool of_device_is_compatible(struct device_node *node,const char *name)
{ assert(!strcmp(name,"qcom,snps-dwc3")); return node->compatible; }
static int of_property_read_string(struct device_node *node,const char *key,const char **value)
{ assert(!strcmp(key,"usb-psy-name")); *value=node->name; return node->name?0:-1; }
static void of_node_put(struct device_node *node) { if(node)node->puts++; }
static void __module_get(void *module) { assert(module==THIS_MODULE); module_gets++; }
#define dev_info(dev,format) do { (void)(dev); assert(!strcmp(format,"native DWC3 supply retained until next boot\n")); logs++; } while(0)
#include "actual-retain.inc"
static void reset(void) { legacy=flat=NULL; native_retained=false; module_gets=logs=legacy_lookups=flat_lookups=0; }
static void check(int held) { assert(module_gets==held && logs==held && native_retained==(bool)held); }
int main(void)
{
 struct device dev={0}; struct device_node a,b;
 reset();samurai_usb_retain_for_native_consumer(&dev);check(0);assert(legacy_lookups==1&&flat_lookups==1);
 reset();a=(struct device_node){false,false,"samurai-usb-input",0};legacy=&a;
 samurai_usb_retain_for_native_consumer(&dev);check(1);assert(a.puts==1&&flat_lookups==0); /* legacy behavior unchanged */
 reset();b=(struct device_node){true,true,"samurai-usb-input",0};flat=&b;
 samurai_usb_retain_for_native_consumer(&dev);check(1);assert(b.puts==1);
 samurai_usb_retain_for_native_consumer(&dev);check(1);assert(b.puts==1&&flat_lookups==1); /* hold once */
 reset();a=(struct device_node){true,true,"unrelated",0};b=(struct device_node){true,true,"samurai-usb-input",0};legacy=&a;flat=&b;
 samurai_usb_retain_for_native_consumer(&dev);check(1);assert(a.puts==1&&b.puts==1);
 reset();b=(struct device_node){false,true,"samurai-usb-input",0};flat=&b;
 samurai_usb_retain_for_native_consumer(&dev);check(0);assert(b.puts==1);
 reset();b=(struct device_node){true,false,"samurai-usb-input",0};flat=&b;
 samurai_usb_retain_for_native_consumer(&dev);check(0);assert(b.puts==1);
 reset();b=(struct device_node){true,true,NULL,0};flat=&b;
 samurai_usb_retain_for_native_consumer(&dev);check(0);assert(b.puts==1);
 reset();b=(struct device_node){true,true,"samurai-usb-input-extra",0};flat=&b;
 samurai_usb_retain_for_native_consumer(&dev);check(0);assert(b.puts==1);
 reset();a=(struct device_node){true,true,"samurai-usb-input",0};b=(struct device_node){true,true,"samurai-usb-input",0};legacy=&a;flat=&b;
 samurai_usb_retain_for_native_consumer(&dev);check(1);assert(a.puts==1&&b.puts==0&&flat_lookups==0);
 reset();native_retained=true;b=(struct device_node){true,true,"samurai-usb-input",0};flat=&b;
 samurai_usb_retain_for_native_consumer(&dev);assert(module_gets==0&&logs==0&&native_retained&&flat_lookups==0);
 puts("{\"actual_function_cases\":11,\"passed\":true}");return 0;
}
