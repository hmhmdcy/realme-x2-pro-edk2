#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <stddef.h>
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define MFD_CELL_NAME(n) { n }
#define MFD_CELL_RES(n,r) { n }
#define GFP_KERNEL 0
#define GPIOD_OUT_LOW 0
#define IRQF_SHARED 1
#define PLATFORM_DEVID_AUTO -1
#define IS_ERR(p) ((intptr_t)(p)<0 && (intptr_t)(p)>-4096)
#define PTR_ERR(p) ((int)(intptr_t)(p))
#define ERR_PTR(n) ((void *)(intptr_t)(n))
struct device { void *of_node; void *data; };
struct i2c_client { struct device dev; int irq, addr; void *adapter; };
struct regmap { int v; };
struct regmap_irq_chip_data { int v; };
struct irq_domain { int v; };
struct fwnode_handle { int v; };
struct gpio_desc { int v; };
struct mfd_cell { const char *name; };
static int qcom_mfd_regmap_cfg,pm8008_regmap_cfg_2,pm8008_irq_chip;
static struct regmap maps[2];
static struct i2c_client second;
static struct gpio_desc gpio;
static struct regmap_irq_chip_data irqdata;
static struct fwnode_handle fwnode;
static struct irq_domain irqdomain;
static char namebuf[]="pm8008/internal";
static int fail_at, stage, allocations, irq_calls, cells_count, release_calls;
static const struct mfd_cell *published;
static struct irq_domain *published_domain;
static int step(void) { stage++; return stage==fail_at; }
static void dev_err(struct device *d,const char *fmt,...) { (void)d;(void)fmt; }
static struct i2c_client *devm_i2c_new_dummy_device(struct device *d,void *a,int addr)
{ (void)d;(void)a;assert(addr==9); return step()?ERR_PTR(-EIO):&second; }
static struct regmap *devm_regmap_init_i2c(struct i2c_client *c,void *cfg)
{ (void)cfg;assert(stage==(c==&second?1:3));return step()?ERR_PTR(-EIO):&maps[c==&second?1:0]; }
static int regmap_attach_dev(struct device *d,struct regmap *r,void *cfg)
{ (void)d;(void)cfg;assert(r==&maps[1]);return step()?-EIO:0; }
static struct gpio_desc *devm_gpiod_get_optional(struct device *d,const char *n,int flags)
{ (void)d;assert(!strcmp(n,"reset")&&flags==GPIOD_OUT_LOW);return step()?ERR_PTR(-EIO):&gpio; }
static void usleep_range(int a,int b) { assert(a==1000&&b==2000); }
static char *devm_kasprintf(struct device *d,int f,const char *fmt,void *n)
{ (void)d;(void)f;(void)fmt;(void)n;allocations++;return step()?NULL:namebuf; }
static char *strreplace(char *s,char a,char b) { for(char *p=s;*p;p++)if(*p==a)*p=b;return s; }
static struct fwnode_handle *irq_domain_alloc_named_fwnode(char *s)
{ (void)s;allocations++;return step()?NULL:&fwnode; }
static void irq_domain_free_fwnode(struct fwnode_handle *f) { assert(f==&fwnode);release_calls++; }
static int devm_add_action_or_reset(struct device *d,void (*fn)(void *),void *data)
{ (void)d;if(step()){fn(data);return -EIO;}return 0; }
static int devm_regmap_add_irq_chip_fwnode(struct device *d,struct fwnode_handle *f,struct regmap *r,int irq,int flags,int index,void *chip,struct regmap_irq_chip_data **out)
{ (void)d;assert(f==&fwnode&&r==&maps[0]&&flags==IRQF_SHARED&&index==0&&chip==&pm8008_irq_chip);irq_calls++;if(step()||irq==0)return -EIO;*out=&irqdata;return 0; }
static struct irq_domain *regmap_irq_get_domain(struct regmap_irq_chip_data *data)
{ assert(data==&irqdata);return &irqdomain; }
static void dev_set_drvdata(struct device *d,void *data) { d->data=data; }
static int devm_mfd_add_devices(struct device *d,int id,const struct mfd_cell *cells,int n,void *res,int base,struct irq_domain *domain)
{ (void)d;assert(id==PLATFORM_DEVID_AUTO&&res==NULL&&base==0);if(step())return -EIO;published=cells;cells_count=n;published_domain=domain;return 0; }
/* The real driver arrays, release callback and probe are inserted here. */

