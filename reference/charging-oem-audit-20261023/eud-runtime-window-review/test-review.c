#include "fake-eud-os.h"
#include "candidate-functions.inc"
#include "nbcon-functions.inc"

static struct eud_port up;
static struct uart_state state;
static struct platform_device device;
static u32 registers[0x2000 / sizeof(u32)], ahb;
static bool initialized;
static void clear(void) {
    if (initialized) {
        pthread_mutex_destroy(&up.port.lock);
        pthread_mutex_destroy(&up.tx_mutex.lock);
    }
    memset(&up, 0, sizeof(up)); memset(&state, 0, sizeof(state));
    memset(registers, 0, sizeof(registers));
    pthread_mutex_init(&up.port.lock, NULL); pthread_mutex_init(&up.tx_mutex.lock, NULL);
    initialized = true;
    up.port.membase = registers; up.port.state = &state;
    up.ahb2phy_cfg = &ahb; up.original_ahb2phy_cfg = 0x77; ahb = 0x11;
    up.rx_irq_started = true; device.dev.data = &up.port;
    eud = &up; eud_reboot_pending = false; eud_window_orphan = 0;
    mmio_reads = mmio_writes = irq_disables = irq_enables = irq_syncs = 0;
    schedules = cancels = restarts = uart_removes = frees = 0;
    stop_at_join = join_reached = join_released = false;
    test_current_work = NULL;
}
static void enqueue(void) {
    memcpy(state.port.xmit_fifo.data, "ABCD", 4); state.port.xmit_fifo.count = 4;
}
static struct eud_com_window_result r;
static void quiet(void) { assert(!eud_com_quiet_begin(&r)); assert(r.software_quiet); }
static void *begin_thread(void *unused) { quiet(); return NULL; }
static void *remove_thread(void *unused) { eud_remove(&device); return NULL; }


static void reset_review(void){
 review_paused=review_release=review_join_waiting=review_begin_done=review_tx_running=false;
 review_writer=review_borrower=review_pause_once=false;
 review_unlock_hook=review_mod_hook=review_enable_hook=NULL;
 review_tx_mutex=&up.tx_mutex;review_tx_work=&up.tx_work;review_quiet=&up.window_quiet;
 review_forbid_mmio=true;
}
static void wait_for(bool *value){
 struct timespec deadline;assert(!clock_gettime(CLOCK_REALTIME,&deadline));deadline.tv_sec+=3;
 assert(!pthread_mutex_lock(&review_lock));
 while(!*value){int ret=pthread_cond_timedwait(&review_cond,&review_lock,&deadline);assert(!ret);}
 assert(!pthread_mutex_unlock(&review_lock));
}
static void pause_here(void){
 assert(!pthread_mutex_lock(&review_lock));review_paused=true;pthread_cond_broadcast(&review_cond);
 while(!review_release)pthread_cond_wait(&review_cond,&review_lock);
 assert(!pthread_mutex_unlock(&review_lock));
}
static void pause_writer_uart(void){if(review_writer&&!review_pause_once){review_pause_once=true;pause_here();}}
static void release_writer(void){
 assert(!pthread_mutex_lock(&review_lock));review_release=true;pthread_cond_broadcast(&review_cond);
 assert(!pthread_mutex_unlock(&review_lock));
}
static void *review_begin(void *unused){
 review_borrower=true;quiet();
 assert(!pthread_mutex_lock(&review_lock));review_begin_done=true;pthread_cond_broadcast(&review_cond);
 assert(!pthread_mutex_unlock(&review_lock));return NULL;
}
static void *review_tx(void *unused){
 review_writer=true;test_current_work=&up.tx_work;
 assert(!pthread_mutex_lock(&review_lock));review_tx_running=true;pthread_cond_broadcast(&review_cond);
 assert(!pthread_mutex_unlock(&review_lock));
 eud_tx_work(&up.tx_work);
 assert(!pthread_mutex_lock(&review_lock));review_tx_running=false;pthread_cond_broadcast(&review_cond);
 assert(!pthread_mutex_unlock(&review_lock));return NULL;
}
static void *review_console(void *unused){
 unsigned long flags;struct nbcon_write_context ctx={"ABCDEFGH",8};review_writer=true;
 eud_console_device_lock(NULL,&flags);eud_console_write_thread(NULL,&ctx);eud_console_device_unlock(NULL,flags);return NULL;
}
static void *review_legacy(void *unused){review_writer=true;eud_console_write_legacy(NULL,"log",3);return NULL;}
static u64 end_cookie;
static struct eud_com_window_result end_result;
static void *review_end(void *unused){assert(!eud_com_quiet_end(end_cookie,&end_result));return NULL;}

int main(void){
 unsigned int groups=0;pthread_t writer,borrower,remover;u64 cookie;
 clear();reset_review();enqueue();eud_shutdown(&up.port);
 assert(state.port.xmit_fifo.count==0&&up.port.icount.tx==4&&mmio_writes==6);
 struct nbcon_write_context ctx={"ABCD",4};unsigned long flags;
 eud_console_device_lock(NULL,&flags);eud_console_write_thread(NULL,&ctx);eud_console_device_unlock(NULL,flags);
 assert(mmio_writes==12&&!up.window_quiet);
 groups++;puts("default shutdown drain and actual nbcon thread remain active");

 clear();reset_review();memcpy(state.port.xmit_fifo.data,"ABCDEFGH",8);state.port.xmit_fifo.count=8;
 review_unlock_hook=pause_writer_uart;
 assert(!pthread_create(&writer,NULL,review_tx,NULL));wait_for(&review_paused);
 assert(!pthread_create(&borrower,NULL,review_begin,NULL));wait_for(&review_join_waiting);
 assert(up.window_quiet&&!review_begin_done);release_writer();
 pthread_join(writer,NULL);pthread_join(borrower,NULL);review_unlock_hook=NULL;
 assert(r.software_quiet&&up.port.icount.tx==4&&state.port.xmit_fifo.count==4&&!mmio_writes);
 cookie=r.cookie;assert(!eud_com_quiet_end(cookie,&r));eud_tx_work(&up.tx_work);
 assert(state.port.xmit_fifo.count==0&&mmio_writes==6);
 groups++;puts("begin joins an actual running TTY worker; undequeued bytes pause");

 clear();reset_review();review_unlock_hook=pause_writer_uart;
 assert(!pthread_create(&writer,NULL,review_console,NULL));wait_for(&review_paused);
 assert(mmio_writes==6);assert(!pthread_create(&borrower,NULL,review_begin,NULL));wait_for(&review_join_waiting);
 assert(up.window_quiet&&!review_begin_done);release_writer();
 pthread_join(writer,NULL);pthread_join(borrower,NULL);review_unlock_hook=NULL;
 assert(r.software_quiet&&mmio_writes==6);
 ctx=(struct nbcon_write_context){"atomic",6};eud_console_write_atomic(NULL,&ctx);assert(mmio_writes==6);
 assert(!eud_com_quiet_end(r.cookie,&r));
 groups++;puts("begin joins nbcon TX mutex; remaining thread and atomic FIFO access gate");

 clear();reset_review();registers[EUD_REG_INT_STATUS_1/sizeof(u32)]=EUD_INT_RX_PENDING;
 review_mod_hook=pause_here;assert(!pthread_create(&writer,NULL,review_legacy,NULL));wait_for(&review_paused);
 quiet();cookie=r.cookie;unsigned int reads=mmio_reads,writes=mmio_writes;
 assert(!up.rx_work.work.pending);release_writer();pthread_join(writer,NULL);review_mod_hook=NULL;
 assert(up.rx_work.work.pending&&up.window_quiet);
 up.rx_work.work.pending=0;eud_rx_work(&up.rx_work.work);
 assert(!up.rx_work.work.pending&&mmio_reads==reads&&mmio_writes==writes);
 assert(!eud_com_quiet_end(cookie,&r));
 groups++;puts("console kick after begin cancellation queues only inert quiet RX work");

 clear();reset_review();up.rx_irq_enabled=up.rx_irq_requested=true;quiet();end_cookie=r.cookie;
 review_enable_hook=pause_here;assert(!pthread_create(&borrower,NULL,review_end,NULL));wait_for(&review_paused);
 assert(!pthread_create(&remover,NULL,remove_thread,NULL));
 assert(pthread_mutex_trylock(&eud_window_lock.lock)==EBUSY);release_writer();
 pthread_join(borrower,NULL);pthread_join(remover,NULL);review_enable_hook=NULL;
 assert(end_result.restored&&!eud&&!eud_window_orphan&&ahb==0x77);
 assert(eud_com_quiet_end(end_cookie,&r)==-ENODEV&&!r.restored);
 clear();reset_review();quiet();cookie=r.cookie;assert(cookie!=end_cookie);
 assert(eud_com_quiet_end(end_cookie,&r)==-ESTALE&&up.window_quiet);
 assert(!eud_com_quiet_end(cookie,&r));
 groups++;puts("end and ordinary remove serialize; old tokens cannot restore rebound endpoint");
 printf("groups=%u\n",groups);return groups==5?0:1;
}
