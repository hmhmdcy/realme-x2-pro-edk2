#ifndef TEST_KERNEL_H
#define TEST_KERNEL_H
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <errno.h>
#include <string.h>
#include <pthread.h>
typedef int64_t s64;
#define BIT(n) (1U<<(n))
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define GFP_KERNEL 0
#define IS_ENABLED(x) 1
#define ERR_PTR(e) ((void *)(intptr_t)(e))
#define PTR_ERR(p) ((intptr_t)(p))
#define IS_ERR(p) ((uintptr_t)(p)>(uintptr_t)-4096)
struct regmap { unsigned int r[8192]; };
struct device { int unused; };
struct tcpc_dev { int unused; };
#define dev_err(...) ((void)0)
struct mutex { pthread_mutex_t m; };
static inline void mutex_init(struct mutex *m) { pthread_mutex_init(&m->m,NULL); }
static inline void mutex_lock(struct mutex *m) { pthread_mutex_lock(&m->m); }
static inline void mutex_unlock(struct mutex *m) { pthread_mutex_unlock(&m->m); }
void *devm_kzalloc(struct device *,size_t,int);
int devm_add_action_or_reset(struct device *,void (*)(void *),void *);
s64 ktime_get_boottime(void);
s64 ktime_to_ms(s64);
void msleep(unsigned int);
int regmap_read(struct regmap *,unsigned int,unsigned int *);
int regmap_update_bits(struct regmap *,unsigned int,unsigned int,unsigned int);
#endif
