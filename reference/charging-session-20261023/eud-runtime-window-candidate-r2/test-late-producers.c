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



static pthread_t producer;
static void finish_producer(void) { release_writer();pthread_join(producer,NULL); }
static void *review_atomic(void *unused) {
 struct nbcon_write_context ctx={"log",3};review_writer=true;
 eud_console_write_atomic(NULL,&ctx);return NULL;
}
static void *review_start_tx(void *unused) { review_writer=true;eud_start_tx(&up.port);return NULL; }
static void start_case(void *(*entry)(void *),bool tty) {
 clear();reset_review();up.console_registered=true;
 review_unregister_hook=NULL;review_uart_remove_hook=NULL;review_schedule_hook=NULL;
 registers[EUD_REG_INT_STATUS_1/sizeof(u32)]=EUD_INT_RX_PENDING;
 if(tty)review_schedule_hook=pause_here;else review_mod_hook=pause_here;
 assert(!pthread_create(&producer,NULL,entry,NULL));wait_for(&review_paused);
}
static void finish_case(const char *name) {
 assert(!eud&&!device.dev.data&&!up.rx_work.work.pending&&!up.tx_work.pending);
 assert(!review_tx_running);printf("ok: %s\n",name);
}
int main(void) {
 start_case(review_legacy,false);quiet();u64 cookie=r.cookie;
 assert(!up.rx_work.work.pending);review_unregister_hook=finish_producer;
 eud_remove(&device);
 assert(up.window_state==EUD_COM_REMOVED&&eud_window_orphan==cookie&&ahb==0x11);
 finish_case("borrowed legacy late RX joined after unregister and UART removal");

 start_case(review_atomic,false);review_unregister_hook=finish_producer;
 eud_remove(&device);assert(ahb==0x77);
 finish_case("ordinary atomic late RX joined after unregister");

 start_case(review_console,false);review_unregister_hook=finish_producer;
 eud_remove(&device);assert(ahb==0x77);
 finish_case("ordinary threaded nbcon late RX joined after unregister");

 start_case(review_start_tx,true);review_uart_remove_hook=finish_producer;
 eud_remove(&device);assert(ahb==0x77);
 finish_case("ordinary late TTY start_tx joined after UART producer removal");
 return 0;
}
