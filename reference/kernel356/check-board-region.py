"""Exercise the actual named firmware-region selection body with OF API stubs."""
from pathlib import Path
import hashlib, json, subprocess
import host

HERE = Path(__file__).resolve().parent
P = host.PRIVATE
s = (HERE/'kernel/camss-icp-a5-boot.c').read_text()
body = s[s.index('static int firmware_region_get'):s.index('int camss_a5_init')]
prefix = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#define CAMSS_A5_FW_WINDOW 0x500000U
#define PAGE_SIZE 4096U
#define IS_ALIGNED(v,a) (!((v)&((a)-1)))
struct device_node {int unused;};
struct device {struct device_node *of_node;};
struct resource {uint64_t start,end;};
static struct device_node consumer,region;
static struct resource selected;
static int name_index,addr_error,refs;
static bool missing,no_map,available;
static int of_property_match_string(struct device_node *n,const char *k,const char *v) {
 assert(n==&consumer&&!strcmp(k,"memory-region-names")&&!strcmp(v,"firmware"));return name_index;
}
static struct device_node *of_parse_phandle(struct device_node *n,const char *k,int i) {
 assert(n==&consumer&&!strcmp(k,"memory-region")&&i==name_index);
 if(missing)return NULL;
 refs++;return &region;
}
static bool of_device_is_available(struct device_node *n){assert(n==&region);return available;}
static bool of_property_present(struct device_node *n,const char *k){assert(n==&region&&!strcmp(k,"no-map"));return no_map;}
static int of_address_to_resource(struct device_node *n,int i,struct resource *r){assert(n==&region&&!i);*r=selected;return addr_error;}
static uint64_t resource_size(const struct resource *r){return r->end-r->start+1;}
static void of_node_put(struct device_node *n){assert(n==&region&&refs==1);refs--;}
'''
main = r'''
int main(void) {
 struct device d={.of_node=&consumer};struct resource r;
 for(unsigned k=0;k<12;k++) {
  name_index=0;addr_error=refs=0;missing=false;no_map=available=true;
  selected=(struct resource){0x9ab00000,0x9affffff};int want=-EINVAL;
  switch(k) {
   case 0:want=0;break;
   case 1:name_index=-ENOENT;want=-ENOENT;break;
   case 2:missing=true;break;
   case 3:no_map=false;break;
   case 4:available=false;break;
   case 5:addr_error=-EIO;want=-EIO;break;
   case 6:selected.start=0;selected.end=CAMSS_A5_FW_WINDOW-1;break;
   case 7:selected.start++;selected.end++;break;
   case 8:selected.end--;break;
   case 9:selected=(struct resource){0x86200000,0x8d6fffff};break;
   case 10:selected.end=selected.start-1;break;
   case 11:name_index=2;want=0;break;
  }
  assert(firmware_region_get(&d,&r)==want&&!refs);
  if(!want)assert(r.start==0x9ab00000&&resource_size(&r)==CAMSS_A5_FW_WINDOW);
 }
 puts("BOARD_REGION_PASS scenarios=12");return 0;
}
'''
src = P/'board-region-test-private.c'; out = P/'board-region-test-private'
src.write_text(prefix+body+main)
q = subprocess.run(['cc','-std=gnu11','-O2','-Wall','-Wextra','-Werror',str(src),'-o',str(out)],capture_output=True)
(P/'board-region-build-private.log').write_bytes(q.stdout+q.stderr); q.check_returncode()
q = subprocess.run([str(out)],capture_output=True)
(P/'board-region-run-private.log').write_bytes(q.stdout+q.stderr); q.check_returncode()
report = dict(stage=356, actual_selection_body_sha256=hashlib.sha256(body.encode()).hexdigest(),
    scenarios=12, named_phandle_selection=True, larger_protected_reservation_rejected=True,
    missing_disabled_or_unmapped_region_rejected=True, malformed_ranges_rejected=True,
    node_reference_balanced=True, of_api_stubs_not_device_test=True, passed=True)
(HERE/'board-region-selection-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(q.stdout.decode().strip())
