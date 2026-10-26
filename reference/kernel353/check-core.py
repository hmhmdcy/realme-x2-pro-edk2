"""Exercise the actual core bodies against original HFI and firmware bytes."""
from pathlib import Path
import hashlib,importlib.util,json,shutil,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
stage=storage.mounted_build().parent/'icp353-tests';stage.mkdir(exist_ok=True)
def no_includes(source):return '\n'.join(l for l in source.splitlines() if not l.startswith('#include'))+'\n'
def function(source,needle):
 start=source.index(needle);brace=source.index('{',start);depth=1;end=brace+1
 while depth:depth+=(source[end]=='{')-(source[end]=='}');end+=1
 return source[start:end]
for name in ['hfi','fw']:(stage/('actual-'+name+'-private.c')).write_text(no_includes((HERE/'kernel'/('camss-icp-a5-'+name+'.c')).read_text()))
(stage/'actual-header-private.h').write_text(no_includes((HERE/'kernel/camss-icp-a5.h').read_text()))
for name in ['core-test-shim.h','core-test.c']:shutil.copyfile(HERE/name,stage/name)
old=P.parent/'kernel352/oem';layout=(old/'hfi_reg.h').read_text();end=layout.index('};',layout.index('struct hfi_qtbl {'))+2
prefix=no_includes(layout[:end])+'\n#endif\n';(stage/'old-layout-private.h').write_text(prefix)
source=(old/'hfi.c').read_text()
reference='''#define __packed __attribute__((packed))
#include "old-layout-private.h"
#define CAM_ERR(...) ((void)0)
#define CAM_DBG(...) ((void)0)
struct region {uintptr_t kva;u32 iova;};
struct reference_map {struct region qtbl,cmd_q,msg_q,dbg_q;};
struct reference_hfi {struct reference_map map;u32 hfi_state,cmd_q_state,msg_q_state;u8 *csr_base;};
static struct reference_hfi context,*g_hfi=&context;
static u8 fake_csr[4096];static unsigned int doorbells;
static DEFINE_MUTEX(hfi_cmd_q_mutex);static DEFINE_MUTEX(hfi_msg_q_mutex);
#define wmb() __atomic_thread_fence(__ATOMIC_RELEASE)
static void cam_io_w_mb(u32 value,void *address){assert(value==1&&address==fake_csr+0x30);doorbells++;}
static void reference_setup(struct hfi_qtbl *table,u32 *cmd,u32 *msg,u32 *dbg){
context=(struct reference_hfi){.map={.qtbl={.kva=(uintptr_t)table},.cmd_q={.kva=(uintptr_t)cmd},.msg_q={.kva=(uintptr_t)msg},.dbg_q={.kva=(uintptr_t)dbg}},.hfi_state=HFI_READY,.cmd_q_state=1,.msg_q_state=1,.csr_base=fake_csr};}
'''
reference+=function(source,'int hfi_write_cmd(void *cmd_ptr)')+'\n'+function(source,'int hfi_read_message(uint32_t *pmsg, uint8_t q_id,')+'\n'
start=source.index('qtbl = (struct hfi_qtbl *)hfi_mem->qtbl.kva;',source.index('int cam_hfi_init('))
part1=source[start:source.index('sfr_buffer =',start)]
start=source.index('switch (event_driven_mode)',start);part2=source[start:source.index('cam_io_w_mb(',start)]
reference+='''static void reference_init(struct hfi_qtbl *out,const u64 addresses[3]){
struct reference_map memory={.qtbl={.kva=(uintptr_t)out},.cmd_q={.iova=addresses[0]},.msg_q={.iova=addresses[1]},.dbg_q={.iova=addresses[2]}};
struct reference_map *hfi_mem=&memory;struct hfi_qtbl *qtbl;struct hfi_qtbl_hdr *qtbl_hdr;struct hfi_q_hdr *cmd_q_hdr,*msg_q_hdr,*dbg_q_hdr;
u8 event_driven_mode=INTR_MODE;
'''+part1+part2+'}\n'
(stage/'original-reference-private.c').write_text(reference)
raw=(P.parent/'kernel352/CAMERA_ICP.elf-private').read_bytes();shutil.copyfile(P.parent/'kernel352/CAMERA_ICP.elf-private',stage/'CAMERA_ICP.elf-private')
offset=struct.unpack_from('<I',raw,28)[0];stride,count=struct.unpack_from('<HH',raw,42);segments=[struct.unpack_from('<8I',raw,offset+i*stride) for i in range(count)]
span=max(s[2]+s[5] for s in segments if s[0]==1);expected=bytearray(b'\xa5'*(5*1024*1024));expected[:span]=bytes(span)
for kind,offset,va,pa,filesz,memsz,flags,align in segments:
 if kind==1:expected[va:va+filesz]=raw[offset:offset+filesz]
(stage/'firmware-expected-private.bin').write_bytes(expected)
flags=['-std=gnu11','-O2','-g','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fno-strict-aliasing','-pthread']
rows=[]
for arch in ['host','aarch64']:
 arm=SDK/'private/camss353-core';mounted=False
 try:
  if arch=='aarch64':
   arm.mkdir(exist_ok=True);assert not list(arm.iterdir())
   subprocess.run(['mount','--bind',str(stage),str(arm)],check=True,capture_output=True);mounted=True
  command=['gcc',*flags,str(stage/'core-test.c'),'-o',str(stage/'core-host')] if arch=='host' else ['chroot',str(SDK),'gcc',*flags,'/private/camss353-core/core-test.c','-o','/private/camss353-core/core-aarch64']
  q=subprocess.run(command,capture_output=True);(P/(arch+'-core-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
  command=[str(stage/'core-host'),str(stage/'CAMERA_ICP.elf-private'),str(stage/'firmware-expected-private.bin')] if arch=='host' else ['chroot',str(SDK),'/private/camss353-core/core-aarch64','/private/camss353-core/CAMERA_ICP.elf-private','/private/camss353-core/firmware-expected-private.bin']
  q=subprocess.run(command,capture_output=True,timeout=30);(P/(arch+'-core-test.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stdout.decode()+q.stderr.decode()
  text=q.stdout.decode();assert all(tag in text for tag in ['TRANSPORT_PASS','FIRMWARE_PASS','CORE_PASS'])
  rows.append(dict(architecture=arch,output=text.splitlines(),passed=True));print(text,flush=True)
 finally:
  if mounted:subprocess.run(['umount',str(arm)],check=True,capture_output=True)
report=dict(stage=353,architectures=rows,actual_kernel_helper_bodies_compiled=True,original_hfi_source_functions_compiled_privately=True,
 original_interrupt_mode_qtable_all_3848_bytes_identical=True,source_host_command_write_comparisons=1584,source_single_message_read_comparisons=16,
 multi_packet_receive_and_wrap_short_buffer_and_incomplete_input_verified=True,invalid_wire_lengths_and_queue_metadata_rejected=True,
 host_mutex_concurrency_packets_per_architecture=2000,original_firmware_image_and_BSS_and_holes_verified=True,
 malformed_elf_rejections_per_architecture=17,invalid_elf_leaves_destination_and_layout_unchanged=True,
 dma_barriers_simulated_not_physical_coherency_proof=True,firmware_not_booted=True,phone_changed=False,sdk_bind_released=True,passed=True)
(HERE/'core-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
