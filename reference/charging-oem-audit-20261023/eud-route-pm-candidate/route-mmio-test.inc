/* Model only the physical resource/MMIO boundary; whole provider is real C. */
#define __iomem
static bool route_region_held, route_mapping_live, route_region_fail, route_mapping_fail;
static unsigned char route_mmio[0x2000];
static unsigned route_csr_reads, route_live_csr, route_csr_second;
static bool route_change_on_second;
static void *request_mem_region(unsigned long long start,unsigned long long bytes,const char *name)
{assert(start==0x088e0000&&bytes==0x2000&&!strcmp(name,"samurai-eud-off-route"));if(route_region_fail)return NULL;assert(!route_region_held);route_region_held=true;return route_mmio;}
static void release_mem_region(unsigned long long start,unsigned long long bytes)
{assert(start==0x088e0000&&bytes==0x2000&&route_region_held&&!route_mapping_live);route_region_held=false;}
static void *ioremap(unsigned long long start,unsigned long long bytes)
{assert(start==0x088e0000&&bytes==0x2000&&route_region_held&&!route_mapping_live);if(route_mapping_fail)return NULL;route_mapping_live=true;return route_mmio;}
static void iounmap(void *base){assert(base==route_mmio&&route_mapping_live);route_mapping_live=false;}
static unsigned readl(const void *address)
{assert(address==route_mmio+0x1014&&route_region_held&&route_mapping_live);route_csr_reads++;return route_change_on_second&&route_csr_reads%2==0?route_csr_second:route_live_csr;}

