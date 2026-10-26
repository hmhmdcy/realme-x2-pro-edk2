// SPDX-License-Identifier: MIT
#define _GNU_SOURCE
#include <gst/gst.h>
#include <pthread.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>
static pthread_mutex_t mutex=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t cond=PTHREAD_COND_INITIALIZER;
static int entered,finish,freed;
static gboolean disposing(GstMiniObject *obj)
{
 (void)obj;
 pthread_mutex_lock(&mutex);entered=1;pthread_cond_broadcast(&cond);
 while(!finish)pthread_cond_wait(&cond,&mutex);
 assert(!g_atomic_int_get(&freed));
 pthread_mutex_unlock(&mutex);return TRUE;
}
static void destroyed(gpointer data,GstMiniObject *obj)
{(void)data;(void)obj;g_atomic_int_set(&freed,1);}
static void *last_unref(void *p){gst_buffer_unref(p);return NULL;}
int main(int argc,char **argv)
{
 gst_init(NULL,NULL);
 int unsafe=argc>1 && !strcmp(argv[1],"unsafe-pin");
 for(int i=0;i<64;i++){
  entered=finish=0;g_atomic_int_set(&freed,0);
  GstBuffer *b=gst_buffer_new();
  GST_MINI_OBJECT_CAST(b)->dispose=disposing;
  gst_mini_object_weak_ref(GST_MINI_OBJECT_CAST(b),destroyed,NULL);
  pthread_t t;assert(!pthread_create(&t,NULL,last_unref,b));
  pthread_mutex_lock(&mutex);while(!entered)pthread_cond_wait(&cond,&mutex);
  assert(GST_MINI_OBJECT_REFCOUNT_VALUE(b)==0);
  /* remove_buffer runs while the recycle callback is blocked on its loop. */
  if(unsafe)gst_buffer_ref(b);
  GST_MINI_OBJECT_CAST(b)->dispose=NULL;
  if(unsafe)gst_buffer_unref(b);
  /* A temporary pin resurrects refcount zero, then frees the buffer while
   * its original dispose callback is still executing. */
  assert(!g_atomic_int_get(&freed));
  finish=1;pthread_cond_broadcast(&cond);pthread_mutex_unlock(&mutex);
  assert(!pthread_join(t,NULL));assert(g_atomic_int_get(&freed));
 }
 puts("{\"controlled_dispose_races\":64,\"freed_before_callback_finished\":false}");
 return 0;
}

