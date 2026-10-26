/* Actual BDS functions + whole receiver; only firmware/kernel boundaries fake. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#define STATIC static
#define VOID void
#define IN
#define OUT
#define EFIAPI
#define TRUE true
#define FALSE false
#define EFI_SUCCESS 0
#define EFI_NOT_READY 1
#define EFI_DEVICE_ERROR 2
#define EFI_COMPROMISED_DATA 3
#define EFI_ALREADY_STARTED 4
#define EFI_UNSUPPORTED 5
#define EFI_NOT_FOUND 6
#define EFI_OUT_OF_RESOURCES 7
#define EFI_ERROR(s) ((s)!=EFI_SUCCESS)
#define EVT_NOTIFY_SIGNAL 0x200
#define TPL_CALLBACK 8
#define DEBUG(...) ((void)0)
#define DEBUG_ERROR 1
typedef bool BOOLEAN;
typedef uint32_t UINT32;
typedef uintptr_t UINTN;
typedef uint64_t EFI_STATUS;
typedef void *EFI_EVENT;
typedef struct {uint32_t a;uint16_t b,c;uint8_t d[8];} EFI_GUID;
typedef EFI_GUID efi_guid_t;
#define EFI_GUID(a,b,c,d0,d1,d2,d3,d4,d5,d6,d7) {a,b,c,{d0,d1,d2,d3,d4,d5,d6,d7}}
static EFI_GUID gEfiEventBeforeExitBootServicesGuid;
static void *gST=(void*)1;
typedef void (*notify_fn)(EFI_EVENT,void*);
struct boot_services {
 EFI_STATUS (*CreateEventEx)(UINT32,unsigned int,notify_fn,void*,EFI_GUID*,EFI_EVENT*);
 EFI_STATUS (*CloseEvent)(EFI_EVENT);
 EFI_STATUS (*InstallConfigurationTable)(EFI_GUID*,void*);
};
static struct boot_services services,*gBS=&services;
static void *published,*allocated;
static int allocations,frees,installs,uninstalls,creates,closes,csr_reads,csr_writes,fences;
static int allocation_error,install_error,remove_error,create_error,close_error,query_error;
static bool ignore_write;
static UINT32 csr;
static notify_fn pending;
static void *pending_context;
static void ZeroMem(void *p,size_t n){memset(p,0,n);}
static void MemoryFence(void){fences++;}
static UINT32 MmioRead32(UINTN address){assert(address==0x088e1014);csr_reads++;return csr;}
static void MmioWrite32(UINTN address,UINT32 value){assert(address==0x088e1014&&value==0);csr_writes++;if(!ignore_write)csr=value;}
static void *AllocateReservedPages(UINTN pages){assert(pages==1);allocations++;if(allocation_error)return NULL;assert(!allocated);allocated=aligned_alloc(4096,4096);assert(allocated);memset(allocated,0x5a,4096);return allocated;}
static void FreePages(void *p,UINTN pages){assert(p==allocated&&pages==1&&p!=published);frees++;free(p);allocated=NULL;}
static EFI_STATUS EfiGetSystemConfigurationTable(EFI_GUID *guid,void **value)
{(void)guid;if(query_error)return query_error;if(!published)return EFI_NOT_FOUND;*value=published;return EFI_SUCCESS;}
static EFI_STATUS install(EFI_GUID *guid,void *table)
{(void)guid;if(table){installs++;if(install_error)return install_error;assert(!published);published=table;}else{uninstalls++;if(remove_error)return remove_error;published=NULL;}return EFI_SUCCESS;}
static EFI_STATUS create(UINT32 type,unsigned int tpl,notify_fn fn,void *ctx,EFI_GUID *guid,EFI_EVENT *event)
{assert(type==EVT_NOTIFY_SIGNAL&&tpl==TPL_CALLBACK&&guid==&gEfiEventBeforeExitBootServicesGuid);creates++;if(create_error)return create_error;pending=fn;pending_context=ctx;*event=(void*)2;return EFI_SUCCESS;}
static EFI_STATUS close_event(EFI_EVENT event)
{assert(event==(void*)2);closes++;if(close_error)return close_error;pending=NULL;pending_context=NULL;return EFI_SUCCESS;}
/* ACTUAL_WIRE */
/* ACTUAL_FIRMWARE */

#define __init
#define __initdata
#define __ro_after_init
#define IS_ENABLED(x) 1
#define EFI_INVALID_TABLE_ADDR (~0UL)
#define EFI_BOOT 0
#define EFI_CONFIG_TABLES 1
#define EFI_64BIT 2
#define EFI_RESERVED_TYPE 0
#define EFI_MEMORY_WB 8ULL
#define EFI_MEMORY_RUNTIME (1ULL<<63)
#define EFI_MEMORY_RP (1ULL<<13)
#define EFI_PAGE_SHIFT 12
#define MEMREMAP_WB 1
typedef struct {unsigned int type;uint64_t phys_addr,num_pages,attribute;} efi_memory_desc_t;
static bool efi_features[3],correct_board,table_usable;
static efi_memory_desc_t descriptor;
static int descriptor_error,map_error,maps,unmaps;
static bool mutate_between_reads;
static int efi_guidcmp(efi_guid_t a,efi_guid_t b){return memcmp(&a,&b,sizeof(a));}
static bool efi_config_table_is_usable(const efi_guid_t *guid,unsigned long table){(void)guid;(void)table;return table_usable;}
static bool efi_enabled(unsigned int flag){assert(flag<3);return efi_features[flag];}
static bool of_machine_is_compatible(const char *name){assert(!strcmp(name,"realme,samurai"));return correct_board;}
static int efi_mem_desc_lookup(unsigned long physical,efi_memory_desc_t *out)
{assert(physical==(unsigned long)published);if(descriptor_error)return descriptor_error;*out=descriptor;return 0;}
static void *memremap(unsigned long physical,size_t bytes,unsigned long flags)
{assert(physical==(unsigned long)published&&bytes==64&&flags==MEMREMAP_WB);maps++;return map_error?NULL:published;}
static void memunmap(void *p){assert(p==published);unmaps++;}
static void rmb(void){if(mutate_between_reads)((struct samurai_eud_handoff*)published)->checksum^=1;}
/* ACTUAL_KERNEL */

static void reset(void)
{
 /* Model power-off destruction of retained firmware pages only. This is
  * fixture disposal, never a production successful uninstall/free claim. */
 published=NULL;if(allocated){free(allocated);allocated=NULL;}
 memset(&mSamuraiEudOffHandoff,0,sizeof(mSamuraiEudOffHandoff));
 services=(struct boot_services){create,close_event,install};gBS=&services;gST=(void*)1;
 allocations=frees=installs=uninstalls=creates=closes=csr_reads=csr_writes=fences=0;
 allocation_error=install_error=remove_error=create_error=close_error=query_error=0;
 ignore_write=false;csr=1;pending=NULL;pending_context=NULL;
 handoff_seen=false;handoff_physical=EFI_INVALID_TABLE_ADDR;
 for(unsigned int i=0;i<3;i++)efi_features[i]=true;
 correct_board=table_usable=true;descriptor_error=map_error=maps=unmaps=0;mutate_between_reads=false;
}
static void callback(void){assert(pending);pending((void*)2,pending_context);}
static void boot_record(void)
{
 assert(SamuraiArmEudOffHandoff()==EFI_SUCCESS&&published==allocated);
 assert(!((struct samurai_eud_handoff*)published)->commit&&!csr_writes);
 callback();assert(samurai_eud_handoff_valid(published,(unsigned long)published));
 descriptor=(efi_memory_desc_t){EFI_RESERVED_TYPE,(unsigned long)published,1,EFI_MEMORY_WB};
 samurai_eud_handoff_config(&mSamuraiEudHandoffGuid,(unsigned long)published);
}
static void reject_untouched(int expected)
{
 struct samurai_eud_handoff out,poison;memset(&poison,0x5a,sizeof(poison));out=poison;
 int before=csr_reads+csr_writes;assert(samurai_eud_handoff_copy(&out)==expected&&!memcmp(&out,&poison,sizeof(out)));
 assert(csr_reads+csr_writes==before);
}
int main(void)
{
 assert(sizeof(struct samurai_eud_handoff)==64&&offsetof(struct samurai_eud_handoff,checksum)==56);
 for(unsigned int i=0;i<3;i++){
  reset();csr=i==0?0:(i==1?1:0x01010101);boot_record();struct samurai_eud_handoff out;
  assert(!samurai_eud_handoff_copy(&out)&&out.after_csr==0&&maps==1&&unmaps==1&&fences>=2);
  int w=csr_writes;callback();assert(csr_writes==w&&samurai_eud_handoff_valid(published,(unsigned long)published));
  SamuraiDisarmEudOffHandoff();assert(!published&&!allocated&&frees==1&&uninstalls==1);
 }
 puts("1 actual producer/receiver round-trip, exact whole-word set, commit-last, one CSR0 attempt and reserved-page cleanup");

 reset();assert(!SamuraiArmEudOffHandoff());csr=0x00010101;callback();assert(!csr_writes&&!((struct samurai_eud_handoff*)published)->commit);
 SamuraiDisarmEudOffHandoff();
 reset();assert(!SamuraiArmEudOffHandoff());ignore_write=true;callback();assert(csr_writes==1&&!((struct samurai_eud_handoff*)published)->commit);
 SamuraiDisarmEudOffHandoff();puts("2 unknown pre-word and nonzero readback never publish a successful record");

 reset();allocation_error=1;assert(SamuraiArmEudOffHandoff()==EFI_OUT_OF_RESOURCES&&!creates&&!published&&!allocated);
 reset();install_error=EFI_DEVICE_ERROR;assert(SamuraiArmEudOffHandoff()==EFI_DEVICE_ERROR&&!creates&&!published&&!allocated&&frees==1);
 reset();query_error=EFI_DEVICE_ERROR;assert(SamuraiArmEudOffHandoff()==EFI_DEVICE_ERROR&&!allocations&&!creates);
 reset();published=(void*)4;assert(SamuraiArmEudOffHandoff()==EFI_ALREADY_STARTED&&!allocations&&!installs&&!creates);published=NULL;
 puts("3 allocation/install/query/duplicate failures refuse arm before event or CSR write");

 reset();create_error=EFI_DEVICE_ERROR;assert(SamuraiArmEudOffHandoff()==EFI_DEVICE_ERROR&&!published&&!allocated&&frees==1&&!csr_writes);
 reset();create_error=EFI_DEVICE_ERROR;remove_error=EFI_DEVICE_ERROR;assert(SamuraiArmEudOffHandoff()==EFI_DEVICE_ERROR&&published==allocated&&!frees);
 assert(!((struct samurai_eud_handoff*)published)->commit);
 puts("4 failed event removes the table; failed uninstall retains an invalid reserved page without dangling publication");

 reset();boot_record();close_error=EFI_DEVICE_ERROR;SamuraiDisarmEudOffHandoff();assert(published==allocated&&!frees&&!((struct samurai_eud_handoff*)published)->commit);
 int w=csr_writes;callback();assert(csr_writes==w&&!((struct samurai_eud_handoff*)published)->commit);
 puts("5 loader return invalidates before failed close; a late callback remains cancelled and reserved storage survives");

 reset();reject_untouched(-ENODATA);boot_record();efi_guid_t other=handoff_guid;other.a^=1;
 samurai_eud_handoff_config(&other,0);assert(handoff_physical==(unsigned long)published);
 samurai_eud_handoff_config(&handoff_guid,(unsigned long)published);reject_untouched(-ENODATA);
 samurai_eud_handoff_config(&handoff_guid,(unsigned long)published);reject_untouched(-ENODATA);
 reset();assert(!SamuraiArmEudOffHandoff());callback();table_usable=false;
 samurai_eud_handoff_config(&handoff_guid,(unsigned long)published);reject_untouched(-ENODATA);
 table_usable=true;samurai_eud_handoff_config(&handoff_guid,(unsigned long)published);reject_untouched(-ENODATA);
 puts("6 actual EFI hook ignores other GUIDs and permanently rejects duplicate or unusable current-boot publications");

 for(unsigned int feature=0;feature<3;feature++){reset();boot_record();efi_features[feature]=false;reject_untouched(-EOPNOTSUPP);assert(!maps);}
 reset();boot_record();correct_board=false;reject_untouched(-EOPNOTSUPP);
 reset();boot_record();descriptor_error=-ENOENT;reject_untouched(-ENOENT);assert(!maps);
 puts("7 actual EFI boot/config/64-bit and board provenance gates precede all mapping");

 reset();boot_record();descriptor.type=7;reject_untouched(-EPROTO);
 reset();boot_record();descriptor.attribute=0;reject_untouched(-EPROTO);
 reset();boot_record();descriptor.attribute|=EFI_MEMORY_RUNTIME;reject_untouched(-EPROTO);
 reset();boot_record();descriptor.num_pages=~0ULL;reject_untouched(-EPROTO);
 reset();boot_record();descriptor.phys_addr-=4096;reject_untouched(-EOVERFLOW);
 reset();boot_record();map_error=1;reject_untouched(-ENOMEM);
 puts("8 reserved WB non-runtime memory, whole record range and bounded mapping errors are checked");

 reset();boot_record();mutate_between_reads=true;reject_untouched(-EAGAIN);assert(maps==1&&unmaps==1);
 for(unsigned int i=0;i<64;i++){
  reset();boot_record();((unsigned char*)published)[i]^=1;reject_untouched(-EBADMSG);
 }
 reset();boot_record();struct samurai_eud_handoff *r=published;r->after_csr=1;r->checksum=samurai_eud_handoff_crc(r);reject_untouched(-EBADMSG);
 reset();boot_record();r=published;r->flags^=SAMURAI_EUD_FLAG_WRITE_ATTEMPTED;r->checksum=samurai_eud_handoff_crc(r);reject_untouched(-EBADMSG);
 puts("9 two copies detect tearing; all64 byte corruptions and internally checksummed false status/flags fail untouched");
 reset();puts("10 evidence copy performs zero EUD MMIO; no route lease, IRQ, PD or USB operation is modeled as authorized");
 return 0;
}
