/* Additional kernel/OF/EFI edges for the real combined route/owner fixture.
 * Scheduling in this suite is deterministic; the separate provider suite
 * covers its real pthread/completion/worker concurrency.
 */
#include <ctype.h>
#define __init
#define __initdata
#define MODULE_LICENSE(x)
#define WRITE_ONCE(x,v) ((x)=(v))
#define smp_mb() ((void)0)
#define pm_sleep_ptr(x) (x)
#define subsys_initcall(fn) static int (*route_init_reference)(void) __attribute__((used))=fn
#define WARN_ON(x) ({bool __warn_value=!!(x);assert(!__warn_value);__warn_value;})
#define IORESOURCE_MEM 0x200
typedef uint64_t phys_addr_t;
typedef int atomic_t;
#define ATOMIC_INIT(n) (n)
#define atomic_read(p) (*(p))
#define atomic_set(p,v) (*(p)=(v))
static bool route_board_match=true;
static struct device_node route_node,hardware_node,chosen_node,*of_chosen=&chosen_node;
static int acpi_disabled=1;
static char *saved_command_line="";
static int route_evidence_error,mock_apsd_writes;
static bool unbind_on_route_unlock;
static struct resource *platform_get_resource(struct platform_device*p,unsigned long type,unsigned int i)
{assert(type==IORESOURCE_MEM&&i==0);return p->has_resource?&p->resource:NULL;}
static unsigned long long resource_size(const struct resource*r){return r->end-r->start+1;}
static void platform_set_drvdata(struct platform_device*p,void*d){p->dev.driverdata=d;}
static void *platform_get_drvdata(struct platform_device*p){return p->dev.driverdata;}
static bool device_is_registered(struct device*d){return d->registered;}
static bool of_machine_is_compatible(const char*name){assert(!strcmp(name,"realme,samurai"));return route_board_match;}
static bool of_device_is_available(struct device_node*n){return n->available;}
static bool of_device_is_compatible(struct device_node*n,const char*name){return n->compatible&&!strcmp(n->compatible,name);}
static int of_address_to_resource(struct device_node*n,int i,struct resource*r)
{assert(i==0);*r=(struct resource){n->start,n->start+n->bytes-1,IORESOURCE_MEM};return 0;}
static bool of_property_present(struct device_node*n,const char*name)
{assert(n==&chosen_node);return !strcmp(name,"stdout-path")?n->stdout:n->linux_stdout;}
static char *kstrdup(const char*s,int flags){(void)flags;return strdup(s);}
static char *skip_spaces(const char*s){while(isspace((unsigned char)*s))s++;return (char*)s;}
struct dev_pm_ops {int(*prepare)(struct device*);};
struct of_device_id {const char*compatible;};
struct platform_driver {int(*probe)(struct platform_device*);void(*remove)(struct platform_device*);void(*shutdown)(struct platform_device*);
 struct {const char*name;const struct of_device_id*of_match_table;const struct dev_pm_ops*pm;bool suppress_bind_attrs;} driver;};
static int platform_driver_register(struct platform_driver*p){assert(p->driver.suppress_bind_attrs);return 0;}
/* ACTUAL_WIRE_HEADER */
static struct samurai_eud_handoff mock_handoff;
static int samurai_eud_handoff_copy(struct samurai_eud_handoff*record)
{if(route_evidence_error)return route_evidence_error;*record=mock_handoff;return 0;}
/* ACTUAL_NEXT_ARG */
/* ACTUAL_ROUTE_API */
/* ACTUAL_ROUTE_PROVIDER */
static void publish_route_test(void)
{
 assert(!route_provider&&!producer&&!atomic_read(&route_exclusive));
 /* Fixture-only new-boot state; production has no history reset API. */
 producer_ever_granted=early_producer_seen=false;atomic_set(&boot_evidence_retired,0);
 memset(&route_platform,0,sizeof(route_platform));memset(&route_node,0,sizeof(route_node));memset(&hardware_node,0,sizeof(hardware_node));memset(&chosen_node,0,sizeof(chosen_node));
 route_evidence_error=mock_apsd_writes=0;unbind_on_route_unlock=false;route_board_match=true;acpi_disabled=1;saved_command_line="";
 route_platform.dev.of_node=&route_node;route_platform.dev.registered=true;
 hardware_node.compatible="qcom,sm8150-eud-com";hardware_node.start=0x088e0000;hardware_node.bytes=0x2000;
 phy_node.compatible="snps,dwc3";phy_node.start=0x0a600000;phy_node.bytes=0x10000;
 memset(&mock_handoff,0,sizeof(mock_handoff));mock_handoff.commit=SAMURAI_EUD_HANDOFF_MAGIC;
 mock_handoff.version=1;mock_handoff.bytes=64;mock_handoff.flags=SAMURAI_EUD_FLAG_ATTEMPTED|SAMURAI_EUD_FLAG_DIRECT_FIFO_RETIRED;
 mock_handoff.csr_address=SAMURAI_EUD_HANDOFF_CSR;mock_handoff.table_address=0x90000000;mock_handoff.checksum=samurai_eud_handoff_crc(&mock_handoff);
 assert(samurai_eud_handoff_valid(&mock_handoff,mock_handoff.table_address));assert(!route_probe(&route_platform));
}
