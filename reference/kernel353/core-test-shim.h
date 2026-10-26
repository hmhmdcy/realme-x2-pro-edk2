/* SPDX-License-Identifier: GPL-2.0-only */
#pragma once
#include <assert.h>
#include <elf.h>
#include <errno.h>
#include <inttypes.h>
#include <limits.h>
#include <pthread.h>
#include <sched.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint8_t u8;typedef uint16_t u16;typedef uint32_t u32;typedef uint64_t u64;typedef uint32_t __le32;
struct firmware {size_t size;const u8 *data;};
struct mutex {pthread_mutex_t native;};
static inline void mutex_init(struct mutex *m){assert(!pthread_mutex_init(&m->native,NULL));}
static inline void mutex_lock(struct mutex *m){assert(!pthread_mutex_lock(&m->native));}
static inline void mutex_unlock(struct mutex *m){assert(!pthread_mutex_unlock(&m->native));}
#define DEFINE_MUTEX(n) struct mutex n={PTHREAD_MUTEX_INITIALIZER}
#define READ_ONCE(n) __atomic_load_n(&(n),__ATOMIC_RELAXED)
#define WRITE_ONCE(n,v) __atomic_store_n(&(n),(v),__ATOMIC_RELAXED)
#define cpu_to_le32(n) ((u32)(n))
#define le32_to_cpu(n) ((u32)(n))
#define U32_MAX UINT32_MAX
#define static_assert _Static_assert
#define EXPORT_SYMBOL_GPL(n)
#define min_t(t,a,b) ((t)(a)<(t)(b)?(t)(a):(t)(b))
#define max(a,b) ((a)>(b)?(a):(b))
static inline u32 get_unaligned_le32(const void *p){const u8 *b=p;return (u32)b[0]|(u32)b[1]<<8|(u32)b[2]<<16|(u32)b[3]<<24;}
static inline u16 get_unaligned_le16(const void *p){const u8 *b=p;return (u16)b[0]|(u16)b[1]<<8;}
static inline void put32(void *p,u32 n){u8 *b=p;b[0]=n;b[1]=n>>8;b[2]=n>>16;b[3]=n>>24;}
static inline void put16(void *p,u16 n){u8 *b=p;b[0]=n;b[1]=n>>8;}
static unsigned int dma_reads,dma_writes,dma_full;
static inline void test_rmb(void){__atomic_thread_fence(__ATOMIC_ACQUIRE);__atomic_add_fetch(&dma_reads,1,__ATOMIC_RELAXED);}
static inline void test_wmb(void){__atomic_thread_fence(__ATOMIC_RELEASE);__atomic_add_fetch(&dma_writes,1,__ATOMIC_RELAXED);}
static inline void test_mb(void){__atomic_thread_fence(__ATOMIC_SEQ_CST);__atomic_add_fetch(&dma_full,1,__ATOMIC_RELAXED);}
#define dma_rmb() test_rmb()
#define dma_wmb() test_wmb()
#define dma_mb() test_mb()
