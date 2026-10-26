from pathlib import Path
import hashlib,json,subprocess
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel128';out=Path('/mnt/e/edk2-samurai-out/kernel128');k=Path('/home/cy122/pmos-samurai-kernel128/kernel')
source=(k/'drivers/net/wireless/ath/ath10k/mac.c').read_text();start=source.index('static int ath10k_install_key(');end=source.index('\n}',start)+2;function=source[start:end]
assert 'ar->hw_rev == ATH10K_HW_WCN3990' in function and 'ar->hif.bus == ATH10K_BUS_SNOC' in function
stub='''#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
typedef uint8_t u8;
typedef uint32_t u32;
enum set_key_cmd { SET_KEY, DISABLE_KEY };
enum { ATH10K_HW_WCN3990=1, ATH10K_BUS_SNOC=1, WMI_KEY_GROUP=1, HZ=1000 };
struct ath10k { int conf_mutex,install_key_done,hw_rev; struct { int bus; } hif; };
struct ath10k_vif { struct ath10k *ar; int nohwcrypt; };
struct ieee80211_key_conf { int unused; };
static int send_error,reinitialized,sent,waited,completed;
#define lockdep_assert_held(x) ((void)(x))
static void reinit_completion(int *x) { (void)x; reinitialized++; }
static int ath10k_send_key(struct ath10k_vif *v,struct ieee80211_key_conf *k,
                          enum set_key_cmd cmd,const u8 *m,u32 f) {
 (void)v;(void)k;(void)cmd;(void)m;(void)f;sent++;return send_error;
}
static unsigned long wait_for_completion_timeout(int *x,unsigned long time) {
 (void)x;assert(time==3*HZ);waited++;return completed;
}
'''
tests='''
int main(void) {
 unsigned cases=0;
 int errors[]={0,-EIO,-EINVAL,7};
 unsigned flags[]={0,WMI_KEY_GROUP,8,8|WMI_KEY_GROUP};
 for(int hw=0;hw<3;hw++)for(int bus=0;bus<3;bus++)
 for(int cmd=0;cmd<2;cmd++)for(unsigned f=0;f<4;f++)
 for(int sw=0;sw<2;sw++)for(unsigned e=0;e<4;e++)
 for(int ack=0;ack<2;ack++) {
  struct ath10k ar={.hw_rev=hw,.hif={.bus=bus}};
  struct ath10k_vif v={.ar=&ar,.nohwcrypt=sw};
  struct ieee80211_key_conf key={0};
  send_error=errors[e];completed=ack;reinitialized=sent=waited=0;
  int skip=cmd==DISABLE_KEY && !(flags[f]&WMI_KEY_GROUP) &&
           hw==ATH10K_HW_WCN3990 && bus==ATH10K_BUS_SNOC;
  int expected=sw ? 1 : send_error ? send_error : skip ? 0 : ack ? 0 : -ETIMEDOUT;
  int value=ath10k_install_key(&v,&key,(enum set_key_cmd)cmd,0,flags[f]);
  assert(value==expected);assert(reinitialized==1);assert(sent==!sw);
  assert(waited==(!sw && !send_error && !skip));cases++;
 }
 printf("ACTUAL_KEY_INSTALL_FUNCTION_CASES=%u\\n",cases);
 return 0;
}
'''
c=out/'key-delete-contract-private.c';binary=out/'key-delete-contract-private';c.write_text(stub+function+tests)
subprocess.run(['gcc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-g',str(c),'-o',str(binary)],check=True)
result=subprocess.check_output([str(binary)],text=True);assert result=='ACTUAL_KEY_INSTALL_FUNCTION_CASES=1152\n'
original=(out/'original126-ath10k-mac-private.c').read_text();a=original.index('static int ath10k_install_key(');b=original.index('\n}',a)+2
assert original[:a]==source[:start] and original[b:]==source[end:]
report=dict(candidate=128,actual_patched_function_extracted=True,cases=1152,gcc_werror_asan_ubsan_pass=True,
 nohwcrypt_send_errors_set_group_other_hw_other_bus_and_timeout_paths_covered=True,
 only_successful_wcn3990_snoc_pairwise_delete_skips_wait=True,all_other_source_bytes_preserved=True,
 function_sha256=hashlib.sha256(function.encode()).hexdigest(),not_deployed=True)
(ref/'key-delete-c-test-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
