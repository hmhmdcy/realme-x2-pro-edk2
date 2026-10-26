/* User-mode test boundary only. No kernel, USB or real MMIO access. */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <pthread.h>
#include <unistd.h>
#include <time.h>

typedef uint8_t u8;
typedef uint32_t u32;
typedef uint64_t u64;
typedef int irqreturn_t;
#define IRQ_HANDLED 1
#define __iomem
#define BIT(n) (1u << (n))
#define READ_ONCE(v) (v)
#define container_of(p, type, member) ((type *)((char *)(p) - offsetof(type, member)))
#define min_t(type, a, b) ((type)(a) < (type)(b) ? (type)(a) : (type)(b))
#define max_t(type, a, b) ((type)(a) > (type)(b) ? (type)(a) : (type)(b))
#define WAKEUP_CHARS 256
#define TIOCSER_TEMT 1
struct work_struct { unsigned int pending; };
struct delayed_work { struct work_struct work; };
#define to_delayed_work(p) container_of(p, struct delayed_work, work)
struct mutex { pthread_mutex_t lock; };
#define DEFINE_MUTEX(n) struct mutex n = { PTHREAD_MUTEX_INITIALIZER }
struct kfifo { u8 data[32]; unsigned int head, count; };
struct tty_port { struct kfifo xmit_fifo; };
struct uart_state { struct tty_port port; };
struct uart_port {
    void *membase;
    struct uart_state *state;
    pthread_mutex_t lock;
    struct { unsigned int tx, rx, buf_overrun; } icount;
};
struct console { unsigned int unused; };
struct device { void *data; };
struct platform_device { struct device dev; };
struct dev_pm_ops {
    int (*prepare)(struct device *);
    void (*complete)(struct device *);
    int (*runtime_suspend)(struct device *);
    int (*runtime_resume)(struct device *);
};
static unsigned int mmio_reads, mmio_writes, irq_disables, irq_enables;
static unsigned int schedules, cancels, irq_syncs, restarts, uart_removes, frees;
static unsigned long jiffies;
static void *system_percpu_wq;
static struct console eud_console;
static int eud_uart_driver;
static __thread unsigned int port_depth;
static pthread_mutex_t barrier_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t barrier_cond = PTHREAD_COND_INITIALIZER;
static bool stop_at_join, join_reached, join_released;
static __thread struct work_struct *test_current_work;
static struct work_struct *current_work(void) { return test_current_work; }

static pthread_mutex_t review_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t review_cond=PTHREAD_COND_INITIALIZER;
static bool review_paused,review_release,review_join_waiting,review_begin_done,review_tx_running;
static __thread bool review_writer,review_borrower,review_pause_once;
static void (*review_unlock_hook)(void),(*review_mod_hook)(void),(*review_enable_hook)(void);
static struct mutex *review_tx_mutex;
static struct work_struct *review_tx_work;
static bool *review_quiet;
static bool review_forbid_mmio;
static void review_notice_join(void) {
 assert(!pthread_mutex_lock(&review_lock));review_join_waiting=true;
 pthread_cond_broadcast(&review_cond);assert(!pthread_mutex_unlock(&review_lock));
}
struct nbcon_write_context {const char *outbuf;unsigned int len;};
static bool nbcon_enter_unsafe(struct nbcon_write_context *c){return true;}
static bool nbcon_exit_unsafe(struct nbcon_write_context *c){return true;}
static void cond_resched(void){}
static void migrate_disable(void){}
static void migrate_enable(void){}

static void uart_lock(struct uart_port *p, unsigned long *flags) {
    *flags = 0; assert(!pthread_mutex_lock(&p->lock)); port_depth++;
}
static void uart_unlock(struct uart_port *p) {
    assert(port_depth); port_depth--; assert(!pthread_mutex_unlock(&p->lock)); if(review_unlock_hook)review_unlock_hook();
}
#define uart_port_lock_irqsave(p, f) uart_lock(p, f)
#define uart_port_unlock_irqrestore(p, f) uart_unlock(p)
static void udelay(unsigned int n) {}
static void writel(u32 v, void *p) { assert(!review_forbid_mmio||!review_quiet||!*review_quiet); mmio_writes++; memcpy(p, &v, sizeof(v)); }
#define writel_relaxed writel
#define readl_relaxed readl
static u32 readl(void *p) { u32 v; assert(!review_forbid_mmio||!review_quiet||!*review_quiet); mmio_reads++; memcpy(&v, p, sizeof(v)); return v; }
static void mutex_lock(struct mutex *p) { assert(!port_depth); if(review_borrower&&p==review_tx_mutex)review_notice_join(); assert(!pthread_mutex_lock(&p->lock)); }
static void mutex_unlock(struct mutex *p) { assert(!pthread_mutex_unlock(&p->lock)); }
static bool kfifo_get(struct kfifo *q, u8 *v) {
    if (!q->count) return false;
    *v = q->data[q->head++]; q->count--; return true;
}
static unsigned int kfifo_len(struct kfifo *q) { return q->count; }
static bool uart_tx_stopped(struct uart_port *p) { return false; }
static void uart_write_wakeup(struct uart_port *p) {}
static void (*review_schedule_hook)(void);
static void schedule_work(struct work_struct *p) { if(review_schedule_hook)review_schedule_hook(); p->pending = 1; schedules++; }
static void cancel_work_sync(struct work_struct *p) {
 assert(!port_depth);p->pending=0;cancels++;
 if(p==review_tx_work){
  assert(!pthread_mutex_lock(&review_lock));
  if(review_tx_running){review_join_waiting=true;pthread_cond_broadcast(&review_cond);}
  while(review_tx_running)pthread_cond_wait(&review_cond,&review_lock);
  assert(!pthread_mutex_unlock(&review_lock));
 }
}
static void cancel_delayed_work_sync(struct delayed_work *p) {
    assert(!port_depth); p->work.pending = 0; cancels++;
    assert(!pthread_mutex_lock(&barrier_lock));
    if (stop_at_join) {
        join_reached = true; pthread_cond_broadcast(&barrier_cond);
        while (!join_released) pthread_cond_wait(&barrier_cond, &barrier_lock);
    }
    assert(!pthread_mutex_unlock(&barrier_lock));
}
static void mod_delayed_work(void *q, struct delayed_work *p, unsigned int delay) {
    if(review_mod_hook)review_mod_hook();
    p->work.pending = 1; schedules++;
}
static void schedule_delayed_work(struct delayed_work *p, unsigned int delay) {
    p->work.pending = 1; schedules++;
}
static void disable_irq_nosync(int irq) { irq_disables++; }
static void synchronize_irq(int irq) { assert(!port_depth); irq_syncs++; }
static void enable_irq(int irq) { irq_enables++; if(review_enable_hook)review_enable_hook(); }
static u32 jiffies_to_msecs(unsigned long v) { return (u32)v; }
static unsigned long msecs_to_jiffies(unsigned long v) { return v; }
#define time_after_eq(a, b) ((a) >= (b))
static void fake_print(const char *format, ...) {}
#define pr_info(...) fake_print(__VA_ARGS__)
#define pr_warn(...) fake_print(__VA_ARGS__)
static void pr_flush(unsigned int timeout, bool reset) { assert(!port_depth); }
static void (*review_unregister_hook)(void);
static void unregister_console(struct console *c) { assert(!port_depth); if(review_unregister_hook)review_unregister_hook(); }
static void kernel_restart(char *what) { assert(!port_depth); restarts++; }
static void *dev_get_drvdata(struct device *d) { return d->data; }
static void *platform_get_drvdata(struct platform_device *p) { return p->dev.data; }
static void platform_set_drvdata(struct platform_device *p, void *d) { p->dev.data = d; }
static void free_irq(int irq, void *up) { assert(!port_depth); frees++; }
static void irq_dispose_mapping(int irq) { assert(!port_depth); }
static void (*review_uart_remove_hook)(void);
static void uart_remove_one_port(void *d, struct uart_port *p) { assert(!port_depth); uart_removes++; if(review_uart_remove_hook)review_uart_remove_hook(); }
struct eud_port;
static u8 eud_rx_gic_snapshot_locked(struct eud_port *up) { return 0; }
static const char *eud_rx_source_name(u8 source) { return "fake"; }
static void eud_rx_dispatch(struct eud_port *up) {}
