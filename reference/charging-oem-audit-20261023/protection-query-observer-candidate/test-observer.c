/* Actual production headers/provider functions; only OS/I2C boundaries fake. */
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stdarg.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include "gauge-i2c.h"
#define PAGE_SIZE 4096
#define I2C_LOCK_SEGMENT 1
struct mutex { pthread_mutex_t native; };
struct device { void *data; };
struct device_attribute { int unused; };
static void mutex_lock(struct mutex *m) { assert(!pthread_mutex_lock(&m->native)); }
static void mutex_unlock(struct mutex *m) { assert(!pthread_mutex_unlock(&m->native)); }
static void *dev_get_drvdata(struct device *d) { return d->data; }
static bool sysfs_streq(const char *a, const char *b)
{ size_t n=strlen(a); return n && a[n-1]=='\n' ? n-1==strlen(b) && !memcmp(a,b,n-1) : !strcmp(a,b); }
static int emit(char *buf, size_t offset, const char *format, va_list args)
{
 assert(offset < PAGE_SIZE);
 if (!strcmp(format,"%*phN\n")) {
  int bytes=va_arg(args,int);const unsigned char *p=va_arg(args,const unsigned char *);int n=0;
  for(int i=0;i<bytes;i++)n+=snprintf(buf+offset+n,PAGE_SIZE-offset-n,"%02x",p[i]);
  n+=snprintf(buf+offset+n,PAGE_SIZE-offset-n,"\n");return n;
 }
 int n=vsnprintf(buf+offset,PAGE_SIZE-offset,format,args);assert(n>=0 && (size_t)n<PAGE_SIZE-offset);return n;
}
static int sysfs_emit(char *b,const char *f,...)
{va_list a;va_start(a,f);int n=emit(b,0,f,a);va_end(a);return n;}
static int sysfs_emit_at(char *b,size_t o,const char *f,...)
{va_list a;va_start(a,f);int n=emit(b,o,f,a);va_end(a);return n;}
static pthread_mutex_t bus=PTHREAD_MUTEX_INITIALIZER, gate=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t cond=PTHREAD_COND_INITIALIZER;
static _Thread_local int bus_held;
static _Thread_local bool competitor;
static unsigned int selector, io_count, selects[64], selected_count, word_count;
static unsigned int fail_cmd, pause_cmd;
static int failure, word_fail, word_after;
static bool paused, resume_io, paused_once, competitor_entered;
static unsigned char packets[6][36];
static unsigned int commands[6];
static atomic_ullong fake_clock;
unsigned long long ktime_get_boottime_ns(void) { return atomic_fetch_add(&fake_clock,100)+100; }
static void i2c_lock_bus(struct i2c_adapter *a,int type)
{assert(a && type==I2C_LOCK_SEGMENT && !bus_held);assert(!pthread_mutex_lock(&bus));bus_held=1;}
static void i2c_unlock_bus(struct i2c_adapter *a,int type)
{assert(a && type==I2C_LOCK_SEGMENT && bus_held==1);bus_held=0;assert(!pthread_mutex_unlock(&bus));}
static void checksum(unsigned char *r)
{unsigned sum=0;for(unsigned i=0;i<(unsigned)r[35]-2;i++)sum+=r[i];r[34]=255-(sum&255);}
static void reply(unsigned int cmd,unsigned char *r)
{
 unsigned target=(cmd==0x50 || cmd==0x52 || cmd==0x56)?0x51:cmd;
 for(unsigned i=0;i<6;i++)if(commands[i]==target){memcpy(r,packets[i],36);r[0]=cmd;r[1]=cmd>>8;checksum(r);return;}
 assert(!"no fake reply for unsupported command");
}
int __i2c_smbus_xfer(struct i2c_adapter *a,unsigned short addr,unsigned short flags,
 char direction,unsigned char reg,int size,union i2c_smbus_data *data)
{
 assert(bus_held==1 && a && addr==0x55 && flags==0 && size==I2C_SMBUS_WORD_DATA);io_count++;
 if(competitor){assert(reg==0x0c && direction==I2C_SMBUS_READ);competitor_entered=true;data->word=7;return 0;}
 if(direction==I2C_SMBUS_WRITE){assert(reg==0x3e);selector=data->word;assert(selected_count<64);selects[selected_count++]=selector;
  assert(sm_mac_observe_data_size(selector)>0);
  if(selector==fail_cmd && failure==1)return -EREMOTEIO;return 0;
 }
 assert(reg==0x0a);word_count++;if(word_fail==(int)word_count)return -EIO;
 data->word=word_count==2?word_after:0x00c0;return 0;
}
void usleep_range(unsigned long a,unsigned long b){assert(bus_held==1 && a==1000 && b==1500);}
int __i2c_transfer(struct i2c_adapter *a,struct i2c_msg *m,int count)
{
 assert(bus_held==1 && a && count==2 && m[0].addr==0x55 && m[0].flags==0 && m[0].len==1 && m[0].buf[0]==0x3e);
 assert(m[1].addr==0x55 && m[1].flags==I2C_M_RD && m[1].len==36);io_count++;
 if(selector==pause_cmd && !paused_once){pthread_mutex_lock(&gate);paused_once=paused=true;pthread_cond_broadcast(&cond);while(!resume_io)pthread_cond_wait(&cond,&gate);pthread_mutex_unlock(&gate);}
 reply(selector,m[1].buf);
 if(selector!=fail_cmd)return 2;
 switch(failure){
 case 2:return -ETIMEDOUT;
 case 3:return 1; /* A changed buffer does not certify a complete frame. */
 case 4:m[1].buf[0]^=1;return 2;
 case 5:m[1].buf[34]^=1;return 2;
 case 6:m[1].buf[35]--;return 2;
 case 7:m[1].buf[2]^=1;checksum(m[1].buf);return 2;
 default:return 2;
 }
}
#include "actual-provider.inc"
static struct i2c_adapter adapter;
static struct i2c_client gauge={.adapter=&adapter,.addr=0x55};
static struct sm_protection p;
static struct device dev={.data=&p};
static bool initialized;
static unsigned cases;
static void reset(void)
{
 if(initialized)assert(!pthread_mutex_destroy(&p.lock.native));
 memset(&p,0,sizeof(p));assert(!pthread_mutex_init(&p.lock.native,NULL));initialized=true;p.gauge=&gauge;
 p.id=0x1234;p.safety=3;p.permanent=4;p.operation=5;p.manufacturing=6;p.last_error=-EBUSY;
 io_count=selected_count=word_count=selector=0;fail_cmd=pause_cmd=0;failure=word_fail=0;word_after=0xc0;
 paused=resume_io=paused_once=competitor_entered=false;atomic_store(&fake_clock,0);
}
static void unchanged_health(void)
{assert(p.id==0x1234 && p.safety==3 && p.permanent==4 && p.operation==5 && p.manufacturing==6 && p.last_error==-EBUSY);}
static void show_cached(bool complete)
{
 char data[PAGE_SIZE];unsigned before=io_count;ssize_t n=mac_evidence_show(&dev,NULL,data);
 assert(n>0 && n<PAGE_SIZE && (unsigned)strlen(data)==n && io_count==before && strstr(data,"compatibility_verified=0"));
 if(!complete)assert(strstr(data,"raw=unavailable"));
}
static void *capture_thread(void *out)
{*(ssize_t *)out=mac_evidence_capture_store(&dev,NULL,"capture\n",8);return NULL;}
static void *competitor_thread(void *unused)
{(void)unused;competitor=true;i2c_lock_bus(&adapter,I2C_LOCK_SEGMENT);assert(word_count==2);assert(sm_gauge_word_locked(&gauge,0x0c,false,0)==7);i2c_unlock_bus(&adapter,I2C_LOCK_SEGMENT);return NULL;}
int main(int argc,char **argv)
{
 assert(argc==2);FILE *file=fopen(argv[1],"rb");assert(file);
 for(unsigned i=0;i<6;i++){unsigned char cmd[2];assert(fread(cmd,1,2,file)==2);commands[i]=sm_le16(cmd);assert(fread(packets[i],1,36,file)==36);assert(!sm_mac_validate(packets[i],36,commands[i]));}assert(fgetc(file)==EOF);fclose(file);
 reset();show_cached(false);assert(io_count==0 && !p.evidence.attempted);assert(mac_evidence_capture_store(&dev,NULL,"0x0050",6)==-EINVAL && io_count==0);cases++;
 const unsigned extended[]={0x50,0x52,0x56};
 for(unsigned k=0;k<ARRAY_SIZE(extended);k++){unsigned cmd=extended[k];reset();unsigned char raw[36];struct sm_mac_receipt r;
  i2c_lock_bus(&adapter,I2C_LOCK_SEGMENT);assert(sm_gauge_mac_locked(&gauge,cmd,raw)==-EINVAL && io_count==0);
  assert(!sm_gauge_mac_observe_locked(&gauge,cmd,&r));i2c_unlock_bus(&adapter,I2C_LOCK_SEGMENT);
  assert(r.full_read && r.validate_attempted && r.expected_size==4 && r.raw[35]==8);cases++;
 }
 reset();i2c_lock_bus(&adapter,I2C_LOCK_SEGMENT);
 for(unsigned i=0;i<6;i++){unsigned char raw[36];assert(!sm_gauge_mac_locked(&gauge,commands[i],raw) && !memcmp(raw,packets[i],36));}i2c_unlock_bus(&adapter,I2C_LOCK_SEGMENT);cases++;
 const unsigned denied[]={0,2,0x20,0x21,0x23,0x55,0x60,0x61,0x3672,0xffff,0x10050};
 reset();i2c_lock_bus(&adapter,I2C_LOCK_SEGMENT);for(unsigned i=0;i<ARRAY_SIZE(denied);i++){struct sm_mac_receipt r;assert(sm_gauge_mac_observe_locked(&gauge,denied[i],&r)==-EINVAL && !r.full_read && !r.select_attempted);}i2c_unlock_bus(&adapter,I2C_LOCK_SEGMENT);assert(io_count==0);cases++;
 reset();mutex_lock(&p.lock);assert(!sm_protection_read(&p));mutex_unlock(&p.lock);assert(selected_count==5 && !p.evidence.attempted);for(unsigned i=0;i<5;i++)assert(selects[i]==sm_evidence_commands[i]);cases++;
 reset();assert(mac_evidence_capture_store(&dev,NULL,"capture\n",8)==8);assert(p.evidence.terminal && !p.evidence.error && p.evidence.frames_attempted==8 && word_count==2);
 for(unsigned i=0;i<8;i++){struct sm_mac_receipt *r=&p.evidence.frames[i];assert(selects[i]==sm_evidence_commands[i] && r->full_read && !r->validate_rc && r->started_ns<r->select_end_ns && r->select_end_ns<r->read_end_ns && r->read_end_ns<r->ended_ns);}
 unsigned before=io_count;assert(mac_evidence_capture_store(&dev,NULL,"capture",7)==-EALREADY && before==io_count);show_cached(true);unchanged_health();cases++;
 const int errors[]={0,-EREMOTEIO,-ETIMEDOUT,-EIO,-EAGAIN,-EBADMSG,-EMSGSIZE};
 for(int mode=1;mode<=6;mode++){reset();fail_cmd=0x50;failure=mode;assert(mac_evidence_capture_store(&dev,NULL,"capture",7)==errors[mode]);
  struct sm_mac_receipt *r=&p.evidence.frames[5];assert(p.evidence.terminal && p.evidence.error==errors[mode] && p.evidence.frames_attempted==6 && selected_count==6 && !p.evidence.battery_after_valid);
  assert(r->full_read==(mode>=4));if(mode>=4){assert(r->validate_attempted && r->validate_rc==errors[mode]);unsigned char expected[36];reply(0x50,expected);if(mode==4)expected[0]^=1;if(mode==5)expected[34]^=1;if(mode==6)expected[35]--;assert(!memcmp(r->raw,expected,36));}
  before=io_count;assert(mac_evidence_capture_store(&dev,NULL,"capture",7)==-EALREADY && before==io_count);show_cached(false);unchanged_health();cases++;
 }
 for(int mode=6;mode<=7;mode++){reset();fail_cmd=1;failure=mode;assert(mac_evidence_capture_store(&dev,NULL,"capture",7)==(mode==6?-EMSGSIZE:-ENODEV));assert(selected_count==1 && word_count==0 && !p.evidence.frames[5].attempted);cases++;}
 for(int which=1;which<=2;which++){reset();word_fail=which;assert(mac_evidence_capture_store(&dev,NULL,"capture",7)==-EIO && p.evidence.terminal);assert(selected_count==(which==1?1:8));unchanged_health();cases++;}
 reset();word_after=0xc1;assert(mac_evidence_capture_store(&dev,NULL,"capture",7)==7 && p.evidence.battery_before!=p.evidence.battery_after);show_cached(true);cases++;
 /* Adversarial formatting bound, not fabricated hardware evidence. */
 for(unsigned i=0;i<8;i++){struct sm_mac_receipt *r=&p.evidence.frames[i];r->started_ns=r->select_end_ns=r->read_end_ns=r->ended_ns=~0ULL;r->select_rc=r->read_rc=r->validate_rc=-2147483647;}
 p.evidence.started_ns=p.evidence.ended_ns=p.evidence.battery_before_ns=p.evidence.battery_after_ns=~0ULL;show_cached(true);cases++;
 reset();pause_cmd=0x50;pthread_t first,second,other;ssize_t one=0,two=0;
 assert(!pthread_create(&first,NULL,capture_thread,&one));pthread_mutex_lock(&gate);while(!paused)pthread_cond_wait(&cond,&gate);pthread_mutex_unlock(&gate);
 assert(!pthread_create(&second,NULL,capture_thread,&two));assert(!pthread_create(&other,NULL,competitor_thread,NULL));
 pthread_mutex_lock(&gate);resume_io=true;pthread_cond_broadcast(&cond);pthread_mutex_unlock(&gate);
 assert(!pthread_join(first,NULL) && !pthread_join(second,NULL) && !pthread_join(other,NULL));
 assert(one==8 && two==-EALREADY && selected_count==8 && competitor_entered && p.evidence.terminal);unchanged_health();cases++;
 assert(!pthread_mutex_destroy(&p.lock.native));
 printf("{\"passed\":true,\"actual_function_cases\":%u,\"six_real_packets_replayed\":6,\"new_status_replies_are_synthetic\":true,\"concurrent_capture_and_bus_contender_joined\":true}\n",cases);
 return 0;
}
