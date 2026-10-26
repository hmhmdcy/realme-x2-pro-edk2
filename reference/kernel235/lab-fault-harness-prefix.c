/* Host regmap outcome model; actual lab callback bodies are inserted below. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint8_t u8; typedef uint32_t u32;
#define BIT(n) (1UL << (n))
#define DIV_ROUND_UP(n,d) (((n)+(d)-1)/(d))
#define dev_err(device,...) ((void)(device))
struct mutex { bool held; };
static void mutex_lock(struct mutex *m) { assert(!m->held);m->held=true; }
static void mutex_unlock(struct mutex *m) { assert(m->held);m->held=false; }
struct device { int unused; };
struct regmap;
struct pm8008_imx319_lab_state {
 u32 magic; struct device *parent; struct regmap *primary,*secondary;
 unsigned long mask; struct mutex lock;
 int (*assert_p_reset)(void *);void *reset_cookie;
 bool reset_held,reset_attempted;int reset_error;
 bool fault,claimed,ready,removing,global_initialized,global_original,global_attempted;
 unsigned long attempted_mask,enabled_mask;
};
struct regulator_desc { int unused; };
struct pm8008_lab_rail {
 struct pm8008_imx319_lab_state *state; struct regulator_desc desc;
 unsigned int index,step_rate;int target_uV;
};
struct regulator_dev { struct pm8008_lab_rail *rail; };
static struct pm8008_lab_rail *rdev_get_drvdata(struct regulator_dev *r) { return r->rail; }
static int regulator_list_voltage_linear_range(struct regulator_dev *r,unsigned int sel) {
 if(r->rail->index==0) return sel<=122?528000+(int)sel*8000:-EINVAL;
 return sel<=237?1504000+(int)sel*8000:-EINVAL;
}
struct regmap {
 struct pm8008_imx319_lab_state *owner; bool primary; u8 registers[65536];
 unsigned int polls[7],ready_after;
};
static unsigned int io_count,write_count,fail_at,fail_mode,delay_count;
static unsigned int last_delay,reset_calls;
static int reset_failure;
static bool persistent;
static bool fail_io(void) { io_count++; return fail_at && (io_count==fail_at||(persistent&&io_count>=fail_at)); }
static void valid_map(struct regmap *m) { assert(m&&m->owner&&m->owner->lock.held&&!m->owner->reset_held); }
static int regmap_read(struct regmap *m,unsigned int reg,unsigned int *v) {
 valid_map(m);assert(reg<65536);
 if(fail_io())return -EIO;
 if(!m->primary&&reg>=0x4008&&reg<=0x4608&&((reg-0x4008)%0x100)==0){
  unsigned int index=(reg-0x4008)/0x100;
  m->polls[index]++;
  *v=(m->registers[0x4046+index*0x100]&0x80)&&m->polls[index]>=m->ready_after?0x80:0;
 }else *v=m->registers[reg];
 return 0;
}
static void valid_update(struct regmap *m,unsigned int reg,unsigned int mask,unsigned int value) {
 assert(!(value&~mask));
 if(m->primary){assert(reg==0x950&&mask==1);}
 else {assert((reg==0x4046||reg==0x4346)&&mask==0x80);}
}
static int regmap_update_bits(struct regmap *m,unsigned int reg,unsigned int mask,unsigned int value) {
 valid_map(m);valid_update(m,reg,mask,value);
 bool fail=fail_io();
 if(!fail||fail_mode){m->registers[reg]=(m->registers[reg]&~mask)|(value&mask);write_count++;}
 return fail?-EIO:0;
}
static int regmap_bulk_read(struct regmap *m,unsigned int reg,void *data,unsigned int len) {
 valid_map(m);assert(!m->primary&&(reg==0x4040||reg==0x4340)&&len==2);
 if(fail_io())return -EIO;
 memcpy(data,m->registers+reg,len);return 0;
}
static int regmap_bulk_write(struct regmap *m,unsigned int reg,const void *data,unsigned int len) {
 valid_map(m);assert(!m->primary&&(reg==0x4040||reg==0x4340)&&len==2);
 const u8 *b=data;unsigned int target=b[0]|((unsigned int)b[1]<<8);
 assert(target==(reg==0x4040?1104U:2800U));
 bool fail=fail_io();
 if(!fail||fail_mode){memcpy(m->registers+reg,data,fail&&fail_mode==1?1:len);write_count++;}
 return fail?-EIO:0;
}
static unsigned int get_unaligned_le16(const void *p) { const u8 *b=p;return b[0]|((unsigned int)b[1]<<8); }
static void put_unaligned_le16(unsigned int v,void *p) { u8 *b=p;b[0]=v;b[1]=v>>8; }
static void usleep_range(unsigned int lo,unsigned int hi) { assert(hi==lo+100);delay_count++;last_delay=lo; }
