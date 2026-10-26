from pathlib import Path
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel144')
old=ref.parent/'kernel143/test-eud-functions.c'
text=old.read_text();assert not ref.joinpath('test-eud-handoff.c').exists()
text=text.replace('#include <stdatomic.h>','#include <stdatomic.h>\n#include <stdarg.h>')
text=text.replace('#define EUD_REG_COM_TX_DAT 8','#define EUD_REG_COM_TX_DAT 8\n#define EUD_REG_CSR_EUD_EN 16')
text=text.replace('    bool rx_stopping;','''    bool rx_stopping,tx_stopping,console_registered,rx_irq_requested;
    unsigned int rx_irq,original_ahb2phy_cfg;
    void *ahb2phy_cfg;''')
text=text.replace('static struct console con;','''static struct console con,eud_console;
static bool eud_reboot_pending;
static bool device_enabled=true,fail_initial_flush=false;
static unsigned int hw_writes,hw_reads,flush_calls,unregister_calls,restart_calls,irq_sync_calls,post_disable_tx;
static char notices[4][128];
static unsigned int notice_count;
static _Atomic bool flush_entered;''')
text=text.replace('    assert(irqs_off && mmio_count<4096);','''    if(pointer==(void *)((uintptr_t)up.port.membase+EUD_REG_CSR_EUD_EN)) {
        assert(value==0);device_enabled=false;hw_writes++;return;
    }
    if(!device_enabled)post_disable_tx++;
    assert(irqs_off && mmio_count<4096);''')
needle='#include "eud-generated-functions.h"'
stub='''static void eud_rx_irq_stop_locked(struct eud_port *p,u32 fault) { assert(irqs_off && p->rx_stopping); }
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
'''
text=text.replace(needle,stub+'\n'+needle)
text=text.replace('    atomic_store(&tty_waiting,false);','''    atomic_store(&tty_waiting,false);atomic_store(&flush_entered,false);
    up.tx_stopping=false;up.console_registered=true;up.rx_irq_requested=false;
    up.rx_irq=46;up.original_ahb2phy_cfg=0x22;up.ahb2phy_cfg=(void *)(uintptr_t)8192;
    eud_reboot_pending=false;device_enabled=true;fail_initial_flush=false;notice_count=0;
    hw_writes=hw_reads=flush_calls=unregister_calls=restart_calls=irq_sync_calls=post_disable_tx=0;''')
needle='static void *tty_writer(void *arg)'
extra='''static void drain_notices(void) {
    assert(!irqs_off && !(up.tx_mutex.owned && pthread_equal(up.tx_mutex.owner,pthread_self())));
    while(notice_count) {
        struct nbcon_write_context record=context(notices[0],strlen(notices[0]));
        thread_write(&record);
        notice_count--;memmove(notices,notices+1,notice_count*sizeof(notices[0]));
    }
}
static bool pr_flush(int timeout_ms,bool reset_on_progress) {
    assert(!irqs_off && timeout_ms==1000 && reset_on_progress);
    assert(!(up.tx_mutex.owned && pthread_equal(up.tx_mutex.owner,pthread_self())));
    atomic_store(&flush_entered,true);flush_calls++;
    if(fail_initial_flush)return false;
    drain_notices();return true;
}
static int unregister_console(struct console *console) {
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
'''
text=text.replace(needle,extra+'\n'+needle)
needle='    assert(!up.tx_mutex.owned && !irqs_off && !migrate_count);\n    printf('
assert text.count(needle)==1
new_cases='''    assert(cases==16);
    reset();pr_info("eud: RX46 F1 via=irq irqs=1 fault=0\\n");
    eud_reboot_cmd(&up,2);
#ifdef BASELINE143
    assert(!receipt_issued() && notice_count==2 && !device_enabled && restart_calls==1);
    assert(!flush_calls && !unregister_calls);cases++;
    memcpy(state.port.xmit_fifo.data,"LATE",4);state.port.xmit_fifo.size=4;
    eud_tx_work(&up.tx_work);assert(post_disable_tx>0);cases++;
    printf("BASELINE143 reproduced queued F1 loss and TX after hardware disable; cases: %u\\n",cases);
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
    reset();up.rx_irq_requested=true;pr_info("eud: RX46 F1 via=irq irqs=1 fault=0\\n");
    eud_reboot_cmd(&up,2);assert(irq_sync_calls==1 && receipt_issued());cases++;
    reset();fail_initial_flush=true;pr_info("eud: RX46 F1 via=irq irqs=1 fault=0\\n");
    eud_reboot_cmd(&up,2);assert(receipt_issued() && !notice_count && unregister_calls==1);cases++;
    reset();pr_info("eud: RX46 F1 via=irq irqs=1 fault=0\\n");
    eud_console_device_lock(&con,&flags);
    pthread_t reboot;assert(pthread_create(&reboot,NULL,reboot_worker,NULL)==0);
    spins=0;while(!atomic_load(&flush_entered) && spins++<1000000)sched_yield();
    assert(atomic_load(&flush_entered) && device_enabled);
    w=context(payload,85);eud_console_write_thread(&con,&w);
    eud_console_device_unlock(&con,flags);assert(pthread_join(reboot,NULL)==0);
    assert(receipt_issued() && !device_enabled && !post_disable_tx && restart_calls==1);cases++;
    printf("HANDOFF144 cases passed: %u; queued receipt, shutdown races and late writers covered\\n",cases);
#endif
'''
text=text.replace(needle,new_cases+'\n'+needle)
# Baseline uses declarations shared with the candidate but not their callbacks.
text=text.replace('static bool pr_flush(int timeout_ms,bool reset_on_progress) {','static __attribute__((unused)) bool pr_flush(int timeout_ms,bool reset_on_progress) {')
text=text.replace('static int unregister_console(struct console *console) {','static __attribute__((unused)) int unregister_console(struct console *console) {')
ref.joinpath('test-eud-handoff.c').write_text(text)
print('K144_ASYNC_F1_NEGATIVE_BASELINE_AND_REAL_HANDOFF_FUNCTION_HARNESS_PREPARED')
