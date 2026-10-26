#define _XOPEN_SOURCE 700
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdarg.h>

typedef uint8_t u8;
typedef uint32_t u32;
#define __iomem
#define EUD_TX_CHUNK 4u
#define EUD_TX_BYTE_US 200
#define EUD_TX_FRAME_US 2000
#define EUD_TX_JOURNAL_DEPTH 512
#define EUD_TX_SOURCE_TTY 1
#define EUD_TX_SOURCE_CONSOLE 2
#define EUD_COM_UART_ID 0x90
#define EUD_REG_COM_TX_ID 0
#define EUD_REG_COM_TX_LEN 4
#define EUD_REG_COM_TX_DAT 8
#define EUD_REG_CSR_EUD_EN 16
#define WAKEUP_CHARS 256
#define min(a,b) ((a)<(b)?(a):(b))
#define min_t(type,a,b) min((type)(a),(type)(b))
#define READ_ONCE(value) (value)
#define container_of(ptr,type,member) ((type *)((char *)(ptr)-offsetof(type,member)))
struct kfifo { u8 data[256]; unsigned int size, offset; };
struct tty_port { struct kfifo xmit_fifo; };
struct uart_state { struct tty_port port; };
struct uart_port {
    struct uart_state *state;
    pthread_mutex_t lock;
    struct { unsigned int tx; } icount;
    bool stopped;
    void *membase;
};
struct mutex { pthread_mutex_t lock; pthread_t owner; bool owned; };
struct work_struct { int unused; };
struct delayed_work { int unused; };
struct eud_tx_record { u8 len,source,data[4]; };
struct eud_port {
    struct uart_port port;
    struct work_struct tx_work;
    struct delayed_work rx_work;
    struct mutex tx_mutex;
    unsigned int tx_journal_head,tx_journal_count;
    unsigned long long tx_journal_total;
    struct eud_tx_record tx_journal[EUD_TX_JOURNAL_DEPTH];
    bool rx_stopping,tx_stopping,console_registered,rx_irq_requested;
    unsigned int rx_irq,original_ahb2phy_cfg;
    void *ahb2phy_cfg;
};
struct console { int unused; };
struct nbcon_write_context {
    const char *outbuf;
    unsigned int len;
    bool owned,unsafe;
    unsigned int enter_calls,exit_calls,fail_enter,fail_exit;
};
static struct eud_port *eud;
static struct eud_port up;
static struct uart_state state;
static struct console con,eud_console;
static bool eud_reboot_pending;
static bool device_enabled=true,fail_initial_flush=false;
static unsigned int hw_writes,hw_reads,flush_calls,unregister_calls,restart_calls,irq_sync_calls,post_disable_tx;
static char notices[4][128];
static unsigned int notice_count;
static _Atomic bool flush_entered;
static int system_percpu_wq;
static _Thread_local bool irqs_off;
static _Thread_local unsigned int migrate_count;
static _Thread_local unsigned long time_us,irq_begin,max_irq_hold,lock_entries,reschedules;
static int rx_returns[600],rx_count,rx_index,kicks,cancel_calls,wakeups;
static bool mmio_requires_mutex=true,raw_atomic=false;
static unsigned int mmio_count;
static struct { unsigned int off,value; } mmio[4096];
static _Atomic bool tty_waiting;

static void mutex_lock(struct mutex *m)
{
    if (m->owned && !pthread_equal(m->owner,pthread_self()))
        atomic_store(&tty_waiting,true);
    assert(pthread_mutex_lock(&m->lock)==0);
    m->owner=pthread_self();m->owned=true;
}
static void mutex_unlock(struct mutex *m)
{
    assert(m->owned && pthread_equal(m->owner,pthread_self()));
    m->owned=false;
    assert(pthread_mutex_unlock(&m->lock)==0);
}
static void migrate_disable(void) { migrate_count++; }
static void migrate_enable(void) { assert(migrate_count);migrate_count--; }
static void uart_port_lock_irqsave(struct uart_port *p,unsigned long *flags)
{
    *flags=irqs_off;
    assert(pthread_mutex_lock(&p->lock)==0);
    irqs_off=true;irq_begin=time_us;lock_entries++;
}
static void uart_port_unlock_irqrestore(struct uart_port *p,unsigned long flags)
{
    unsigned long duration=time_us-irq_begin;
    if(duration>max_irq_hold)max_irq_hold=duration;
    assert(irqs_off);
    irqs_off=flags;
    assert(pthread_mutex_unlock(&p->lock)==0);
}
static void udelay(unsigned int us) { assert(irqs_off);time_us+=us; }
static void writel_relaxed(unsigned int value,void *pointer)
{
    if(pointer==(void *)((uintptr_t)up.port.membase+EUD_REG_CSR_EUD_EN)) {
        assert(value==0);device_enabled=false;hw_writes++;return;
    }
    if(!device_enabled)post_disable_tx++;
    assert(irqs_off && mmio_count<4096);
    if(mmio_requires_mutex)
        assert(up.tx_mutex.owned && pthread_equal(up.tx_mutex.owner,pthread_self()));
    if(!raw_atomic && mmio_requires_mutex && migrate_count)
        assert(migrate_count==1);
    mmio[mmio_count].off=(unsigned int)((uintptr_t)pointer-(uintptr_t)up.port.membase);
    mmio[mmio_count++].value=value;
}
static bool kfifo_get(struct kfifo *f,u8 *ch)
{
    assert(irqs_off);
    if(f->offset==f->size)return false;
    *ch=f->data[f->offset++];return true;
}
static unsigned int kfifo_len(struct kfifo *f) { return f->size-f->offset; }
static bool uart_tx_stopped(struct uart_port *p) { return p->stopped; }
static void uart_write_wakeup(struct uart_port *p) { assert(!irqs_off);wakeups++; }
static void cancel_work_sync(struct work_struct *w) { assert(!irqs_off);cancel_calls++; }
static void mod_delayed_work(int queue,struct delayed_work *w,int delay)
{
    assert(!irqs_off);kicks++;
}
static void cond_resched(void) { assert(!irqs_off);reschedules++; }
static int eud_console_rx_locked(struct eud_port *p)
{
    assert(irqs_off);rx_index++;
    return rx_index<=rx_count?rx_returns[rx_index-1]:0;
}
static bool nbcon_enter_unsafe(struct nbcon_write_context *w)
{
    assert(!w->unsafe && irqs_off);
    w->enter_calls++;
    if(!w->owned || w->enter_calls==w->fail_enter){w->owned=false;w->outbuf=(void *)1;return false;}
    w->unsafe=true;return true;
}
static bool nbcon_exit_unsafe(struct nbcon_write_context *w)
{
    assert(w->unsafe);w->unsafe=false;w->exit_calls++;
    if(w->exit_calls==w->fail_exit){w->owned=false;w->outbuf=(void *)1;return false;}
    return w->owned;
}
static void eud_rx_irq_stop_locked(struct eud_port *p,u32 fault) { assert(irqs_off && p->rx_stopping); }
static void synchronize_irq(unsigned int irq) { assert(!irqs_off);irq_sync_calls++; }
static void pr_info(const char *format,...) {
    assert(!irqs_off && notice_count<4);
    va_list ap;va_start(ap,format);vsnprintf(notices[notice_count++],128,format,ap);va_end(ap);
}
static bool pr_flush(int timeout_ms,bool reset_on_progress);
static int unregister_console(struct console *console);
static void writel(unsigned int value,void *pointer) {
    assert(!irqs_off);hw_writes++;
    if(pointer==up.ahb2phy_cfg) { assert(value==up.original_ahb2phy_cfg);return; }
    assert(pointer==(void *)((uintptr_t)up.port.membase+EUD_REG_CSR_EUD_EN) && value==0);
    assert(up.tx_mutex.owned && pthread_equal(up.tx_mutex.owner,pthread_self()) && up.tx_stopping);
    device_enabled=false;
}
static unsigned int readl(void *pointer) {
    assert(!irqs_off);hw_reads++;
    return pointer==up.ahb2phy_cfg?up.original_ahb2phy_cfg:(device_enabled?1:0);
}
#ifdef BASELINE143
static void wmb(void) { assert(!irqs_off); }
#endif
static void kernel_restart(char *what) { assert(!irqs_off && !strcmp(what,"bootloader") && !device_enabled);restart_calls++; }

#include "eud-generated-functions.h"

static void reset(void)
{
    assert(!up.tx_mutex.owned && !irqs_off && migrate_count==0);
    memset(up.tx_journal,0,sizeof(up.tx_journal));
    up.tx_journal_head=up.tx_journal_count=0;up.tx_journal_total=0;
    up.port.state=&state;up.port.stopped=false;up.port.icount.tx=0;up.rx_stopping=false;
    memset(&state,0,sizeof(state));memset(rx_returns,0,sizeof(rx_returns));
    rx_count=rx_index=kicks=cancel_calls=wakeups=0;
    mmio_count=0;mmio_requires_mutex=true;raw_atomic=false;
    time_us=irq_begin=max_irq_hold=lock_entries=reschedules=0;
    atomic_store(&tty_waiting,false);atomic_store(&flush_entered,false);
    up.tx_stopping=false;up.console_registered=true;up.rx_irq_requested=false;
    up.rx_irq=46;up.original_ahb2phy_cfg=0x22;up.ahb2phy_cfg=(void *)(uintptr_t)8192;
    eud_reboot_pending=false;device_enabled=true;fail_initial_flush=false;notice_count=0;
    hw_writes=hw_reads=flush_calls=unregister_calls=restart_calls=irq_sync_calls=post_disable_tx=0;
}
static void verify_payload(const char *payload,unsigned int size,u8 source,unsigned int start)
{
    unsigned int offset=0,index=start;
    while(offset<size){
        struct eud_tx_record *row=&up.tx_journal[index++];
        unsigned int n=min(size-offset,4u);
        assert(row->len==n && row->source==source && !memcmp(row->data,payload+offset,n));
        offset+=n;
    }
}
static struct nbcon_write_context context(const char *s,unsigned int size)
{
    struct nbcon_write_context w={.outbuf=s,.len=size,.owned=true};return w;
}
static void thread_write(struct nbcon_write_context *w)
{
    unsigned long flags=999;
    eud_console_device_lock(&con,&flags);
    assert(flags==0 && !irqs_off && migrate_count==1);
    eud_console_write_thread(&con,w);
    eud_console_device_unlock(&con,flags);
    assert(!up.tx_mutex.owned && !irqs_off && migrate_count==0 && !w->unsafe);
}
static void drain_notices(void) {
    assert(!irqs_off && !(up.tx_mutex.owned && pthread_equal(up.tx_mutex.owner,pthread_self())));
    while(notice_count) {
        struct nbcon_write_context record=context(notices[0],strlen(notices[0]));
        thread_write(&record);
        notice_count--;memmove(notices,notices+1,notice_count*sizeof(notices[0]));
    }
}
static __attribute__((unused)) bool pr_flush(int timeout_ms,bool reset_on_progress) {
    assert(!irqs_off && timeout_ms==1000 && reset_on_progress);
    assert(!(up.tx_mutex.owned && pthread_equal(up.tx_mutex.owner,pthread_self())));
    atomic_store(&flush_entered,true);flush_calls++;
    if(fail_initial_flush)return false;
    drain_notices();return true;
}
static __attribute__((unused)) int unregister_console(struct console *console) {
    assert(console==&eud_console && !irqs_off);
    drain_notices();unregister_calls++;return 0;
}
static bool receipt_issued(void) {
    char bytes[2049];unsigned int size=0;
    for(unsigned int i=0;i<up.tx_journal_count;i++) {
        memcpy(bytes+size,up.tx_journal[i].data,up.tx_journal[i].len);size+=up.tx_journal[i].len;
    }
    bytes[size]=0;return strstr(bytes,"RX46 F1")!=NULL;
}
#ifndef BASELINE143
static void *reboot_worker(void *arg) { eud_reboot_cmd(&up,2);assert(!irqs_off && !migrate_count);return NULL; }
#endif

static void *tty_writer(void *arg)
{
    eud_tx_work(&up.tx_work);
    assert(!irqs_off && max_irq_hold<=3200 && !migrate_count);
    return NULL;
}
int main(void)
{
    unsigned int cases=0;
    char payload[85];memset(payload,'A',sizeof(payload));
    memset(&up,0,sizeof(up));
    assert(pthread_mutex_init(&up.port.lock,NULL)==0);
    assert(pthread_mutex_init(&up.tx_mutex.lock,NULL)==0);
    up.port.membase=(void *)(uintptr_t)4096;eud=&up;
    reset();struct nbcon_write_context w=context(payload,sizeof(payload));thread_write(&w);
    assert(time_us==69800 && max_irq_hold==3200 && up.tx_journal_count==22 && rx_index==23);
    assert(lock_entries==22 && reschedules==22);verify_payload(payload,sizeof(payload),2,0);cases++;

    reset();w=context(payload,0);thread_write(&w);assert(!mmio_count && !rx_index);cases++;
    reset();w=context(payload,sizeof(payload));w.fail_enter=1;thread_write(&w);
    assert(!mmio_count && !rx_index && !kicks);cases++;
    reset();w=context(payload,sizeof(payload));w.fail_exit=4;thread_write(&w);
    assert(up.tx_journal_count==4 && w.exit_calls==4);verify_payload(payload,16,2,0);cases++;
    reset();w=context(payload,sizeof(payload));w.fail_enter=5;thread_write(&w);
    assert(up.tx_journal_count==4 && w.enter_calls==5);verify_payload(payload,16,2,0);cases++;

    reset();rx_count=1;rx_returns[0]=-28;w=context(payload,sizeof(payload));thread_write(&w);
    assert(rx_index==1 && kicks==1 && up.tx_journal_count==22);cases++;
    reset();rx_count=3;rx_returns[2]=-22;w=context(payload,sizeof(payload));thread_write(&w);
    assert(rx_index==3 && kicks==1 && up.tx_journal_count==22);cases++;
    reset();rx_count=2;rx_returns[1]=2;w=context(payload,sizeof(payload));thread_write(&w);
    assert(kicks==1 && rx_index==23);cases++;
    reset();up.rx_stopping=true;rx_count=1;rx_returns[0]=2;
    w=context(payload,sizeof(payload));thread_write(&w);assert(!kicks);cases++;

    reset();mmio_requires_mutex=false;raw_atomic=true;irqs_off=true;
    w=context(payload,sizeof(payload));eud_console_write_atomic(&con,&w);
    assert(irqs_off && time_us==69800 && max_irq_hold==69800);
    assert(up.tx_journal_count==22);verify_payload(payload,sizeof(payload),2,0);irqs_off=false;cases++;
    reset();mmio_requires_mutex=false;raw_atomic=true;irqs_off=true;
    w=context(payload,sizeof(payload));w.fail_enter=1;eud_console_write_atomic(&con,&w);
    assert(!mmio_count && !w.unsafe);irqs_off=false;cases++;

    reset();memcpy(state.port.xmit_fifo.data,payload,85);state.port.xmit_fifo.size=85;
    eud_tx_work(&up.tx_work);
    assert(!up.tx_mutex.owned && !irqs_off && max_irq_hold==3200 && wakeups==1 && up.port.icount.tx==85);
    verify_payload(payload,85,1,0);cases++;
    reset();memcpy(state.port.xmit_fifo.data,payload,85);state.port.xmit_fifo.size=85;
    eud_shutdown(&up.port);
    assert(!up.tx_mutex.owned && !irqs_off && max_irq_hold==3200 && cancel_calls==1);
    verify_payload(payload,85,1,0);cases++;
    reset();up.port.state=NULL;eud_tx_work(&up.tx_work);eud_shutdown(&up.port);
    assert(!mmio_count && cancel_calls==1 && !up.tx_mutex.owned);cases++;
    reset();up.port.stopped=true;state.port.xmit_fifo.size=85;eud_tx_work(&up.tx_work);
    assert(!mmio_count && !state.port.xmit_fifo.offset && !up.tx_mutex.owned);cases++;

    reset();memset(state.port.xmit_fifo.data,'T',12);state.port.xmit_fifo.size=12;
    unsigned long flags;
    eud_console_device_lock(&con,&flags);
    pthread_t tty;assert(pthread_create(&tty,NULL,tty_writer,NULL)==0);
    unsigned int spins=0;while(!atomic_load(&tty_waiting) && spins++<1000000)sched_yield();
    assert(atomic_load(&tty_waiting));
    w=context(payload,sizeof(payload));eud_console_write_thread(&con,&w);
    assert(up.tx_journal_count==22);
    eud_console_device_unlock(&con,flags);assert(pthread_join(tty,NULL)==0);
    assert(up.tx_journal_count==25);verify_payload(payload,85,2,0);
    verify_payload("TTTTTTTTTTTT",12,1,22);cases++;
    assert(cases==16);
    reset();pr_info("eud: RX46 F1 via=irq irqs=1 fault=0\n");
    eud_reboot_cmd(&up,2);
#ifdef BASELINE143
    assert(!receipt_issued() && notice_count==2 && !device_enabled && restart_calls==1);
    assert(!flush_calls && !unregister_calls);cases++;
    memcpy(state.port.xmit_fifo.data,"LATE",4);state.port.xmit_fifo.size=4;
    eud_tx_work(&up.tx_work);assert(post_disable_tx>0);cases++;
    printf("BASELINE143 reproduced queued F1 loss and TX after hardware disable; cases: %u\n",cases);
#else
    assert(receipt_issued() && !notice_count && !device_enabled && restart_calls==1);
    assert(flush_calls==1 && unregister_calls==1 && !up.console_registered && up.tx_stopping);
    assert(hw_writes==2 && hw_reads==2 && !post_disable_tx);cases++;
    unsigned int frames=up.tx_journal_count;
    memcpy(state.port.xmit_fifo.data,"LATE",4);state.port.xmit_fifo.size=4;
    eud_tx_work(&up.tx_work);assert(up.tx_journal_count==frames && !post_disable_tx);cases++;
    memcpy(state.port.xmit_fifo.data,"MORE",4);state.port.xmit_fifo.size=4;state.port.xmit_fifo.offset=0;
    eud_shutdown(&up.port);assert(up.tx_journal_count==frames && !post_disable_tx);cases++;
    w=context(payload,85);thread_write(&w);assert(up.tx_journal_count==frames && !post_disable_tx);cases++;
    mmio_requires_mutex=false;raw_atomic=true;irqs_off=true;
    w=context(payload,85);eud_console_write_atomic(&con,&w);irqs_off=false;
    assert(up.tx_journal_count==frames && !post_disable_tx);cases++;
    eud_reboot_cmd(&up,2);assert(restart_calls==1 && flush_calls==1);cases++;
    reset();eud_reboot_cmd(&up,1);assert(device_enabled && !up.rx_stopping && !eud_reboot_pending && !flush_calls);cases++;
    reset();up.rx_irq_requested=true;pr_info("eud: RX46 F1 via=irq irqs=1 fault=0\n");
    eud_reboot_cmd(&up,2);assert(irq_sync_calls==1 && receipt_issued());cases++;
    reset();fail_initial_flush=true;pr_info("eud: RX46 F1 via=irq irqs=1 fault=0\n");
    eud_reboot_cmd(&up,2);assert(receipt_issued() && !notice_count && unregister_calls==1);cases++;
    reset();pr_info("eud: RX46 F1 via=irq irqs=1 fault=0\n");
    eud_console_device_lock(&con,&flags);
    pthread_t reboot;assert(pthread_create(&reboot,NULL,reboot_worker,NULL)==0);
    spins=0;while(!atomic_load(&flush_entered) && spins++<1000000)sched_yield();
    assert(atomic_load(&flush_entered) && device_enabled);
    w=context(payload,85);eud_console_write_thread(&con,&w);
    eud_console_device_unlock(&con,flags);assert(pthread_join(reboot,NULL)==0);
    assert(receipt_issued() && !device_enabled && !post_disable_tx && restart_calls==1);cases++;
    printf("HANDOFF144 cases passed: %u; queued receipt, shutdown races and late writers covered\n",cases);
#endif

    assert(!up.tx_mutex.owned && !irqs_off && !migrate_count);
    printf("EUD actual-function cases passed: %u; normal max IRQ-off 3200 us, legacy 69800 us\n",cases);
    assert(pthread_mutex_destroy(&up.port.lock)==0);
    assert(pthread_mutex_destroy(&up.tx_mutex.lock)==0);
}
