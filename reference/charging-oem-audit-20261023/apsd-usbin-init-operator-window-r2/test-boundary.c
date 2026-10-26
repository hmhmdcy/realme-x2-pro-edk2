/* R1 fake kernel/hardware boundary, new affected tests only. */
#include "test-boundary-prefix.inc"
static int groups;
static void done(const char *s){groups++;printf("ok: %s\n",s);}
static void fixture(const char *name)
{char buf[4096];int nr=reads,nw=writes;assert(state_show(&dev,NULL,buf)>0&&reads==nr&&writes==nw);printf("fixture:%s %s",name,buf);}
static void on(void){hw.raw[2]=0x10;hw.raw[4]=0x20;hw.raw[5]=0x21;}
static void off(void){memset(hw.raw,0,7);}
static void test_61_seconds(void)
{
 setup();assert(control("observe")==7);fixture("observed");on();assert(control("arm")==3);fixture("armed");
 assert(d.state.started_ms==1000&&d.state.deadline_ms==301000&&refs==1);
 tick(62000);assert(d.state.running&&d.state.phase==UI_WAIT_OFF&&!writes&&refs==1);fixture("waiting_after_61s");
 off();tick(62250);tick(62500);assert(!writes);tick(62750);
 assert(writes==1&&hw.cfg==0x40&&d.state.phase==UI_CLEAR_VERIFIED&&d.state.pending_restore&&refs==1);fixture("clear_verified");
 assert(control("commit")==6&&writes==1&&!refs&&!d.state.pending_restore);fixture("committed");
 done("61 seconds remains waiting; new 500ms off evidence permits one masked clear then explicit zero-IO commit");
}
static void test_expiry(void)
{
 setup();on();assert(control("arm")==3);tick(300999);assert(d.state.running&&!writes&&refs==1);
 tick(301000);assert(d.state.phase==UI_TIMEOUT&&d.state.error==-ETIMEDOUT&&!writes&&!refs);fixture("timeout_at_300s");
 tick(301001);assert(d.state.phase==UI_TIMEOUT&&!writes&&!refs);
 setup();on();assert(control("arm")==3);tick(301001);assert(d.state.phase==UI_TIMEOUT&&!writes&&!refs);
 done("300s absolute boundary: before still waiting; at/after zero-write timeout and released selfref");
}
static void test_last_off_window(void)
{
 setup();on();assert(control("arm")==3);tick(300000);off();tick(300250);tick(300500);tick(300750);
 assert(writes==1&&d.state.prewrite_ms==300750&&d.state.phase==UI_CLEAR_VERIFIED);assert(control("commit")==6&&!refs);
 setup();on();assert(control("arm")==3);tick(300000);off();tick(300750);tick(300999);assert(!writes);
 tick(301000);assert(!writes&&!refs&&d.state.phase==UI_TIMEOUT);
 done("late physical-off writes only with full stable/fresh evidence before deadline; late incomplete evidence cannot spill over");
}
static void test_blocked_and_stale(void)
{
 setup();assert(control("arm")==3);tick(1000);tick(1250);delay_at=reads+17;delay_ms=299500;tick(1500);
 assert(!writes&&!refs&&d.state.phase==UI_TIMEOUT&&d.state.prewrite_ms==301000&&d.state.old_valid);fixture("blocked_prewrite_at_deadline");
 setup();assert(control("arm")==3);tick(1000);tick(1250);delay_at=reads+17;delay_ms=300000;tick(1500);
 assert(!writes&&!refs&&d.state.phase==UI_TIMEOUT&&d.state.prewrite_ms>301000);
 setup();assert(control("arm")==3);tick(1000);tick(1250);delay_at=reads+17;delay_ms=251;tick(1500);
 assert(!writes&&!refs&&d.state.phase==UI_ERROR&&d.state.error==-EAGAIN);fixture("stale_prewrite_rejected");
 done("blocked final config across 300s rejects new write; unchanged 250ms freshness still rejects stale evidence");
}
static void test_restore_window(void)
{
 setup();assert(control("arm")==3);tick(1000);tick(1250);tick(1500);assert(writes==1&&refs==1);
 on();now_ms=2000;assert(control("restore_saved")==13&&d.state.deadline_ms==302000);
 tick(63000);assert(d.state.running&&writes==1&&refs==1);off();tick(63250);tick(63500);tick(63750);
 assert(writes==2&&hw.cfg==0xc0&&d.state.phase==UI_RESTORED&&!refs);fixture("restored_after_61s");
 done("same-instance explicit restore inherits new window but keeps saved-bit/off/fresh gate and unload policy");
}
int main(void)
{setbuf(stdout,NULL);(void)ui_stop;test_61_seconds();test_expiry();test_last_off_window();test_blocked_and_stale();test_restore_window();assert(groups==5);return 0;}
