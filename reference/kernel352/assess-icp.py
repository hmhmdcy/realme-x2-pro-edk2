"""Record the concrete reuse gaps and the retained target firmware layout."""
from pathlib import Path
import json,re,struct
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
tree=json.loads((P/'upstream-camss-tree-private.json').read_bytes()[4:]);names={e['name'] for e in tree['entries']}
make=(P/'upstream/Makefile').read_text();missing=[]
for name in ['camss-icp-hfi.c','camss-bps-cmd.c']:
 assert name.replace('.c','.o') in make and name not in names;missing.append(name)
assert 'camss-ipe.o' not in make
code='\n'.join(p.read_text() for p in (P/'upstream').glob('*.c'))
missing_ipe_apis=[]
for name in ['icp_get','icp_ctx_create','icp_ctx_submit_frame','icp_ctx_destroy','icp_ctx_abort']:
 assert name+'(' in code
 if not re.search(r'\b'+name+r'\s*\([^;{}]*\)\s*\{',code,re.S):missing_ipe_apis.append(name)
def constant(path,name):
 text=path.read_text();m=re.search(r'^#define\s+'+name+r'\s+(0x[0-9a-fA-F]+|[0-9]+)\b',text,re.M);assert m,name
 return int(m.group(1),0)
old=P/'oem/hfi_reg.h';new=P/'upstream/camss-icp-hfi.h';registers=[]
for before,after in [('HFI_REG_FW_VERSION','HFI_REG_FW_VERSION'),('HFI_REG_HOST_ICP_INIT_REQUEST','HFI_REG_HOST_ICP_INIT_REQ'),('HFI_REG_ICP_HOST_INIT_RESPONSE','HFI_REG_ICP_HOST_INIT_RESP'),('HFI_REG_SHARED_MEM_PTR','HFI_REG_SHARED_MEM_PTR'),('HFI_REG_QTBL_PTR','HFI_REG_QTBL_PTR')]:
 a,b=constant(old,before),constant(new,after);assert a!=b;registers.append(dict(role=before,a5_offset=hex(a),prototype_x1e_offset=hex(b)))
raw=(P/'CAMERA_ICP.elf-private').read_bytes();assert raw[:7]==b'\x7fELF\x01\x01\x01'
kind,machine=struct.unpack_from('<HH',raw,16);entry=struct.unpack_from('<I',raw,24)[0];off=struct.unpack_from('<I',raw,28)[0];stride,count=struct.unpack_from('<HH',raw,42)
assert kind==2 and machine==40 and entry==0 and stride==32 and count==3
segments=[]
for i in range(count):
 tag,offset,va,pa,filesz,memsz,flags,align=struct.unpack_from('<8I',raw,off+i*stride)
 assert tag==1 and filesz<=memsz and offset+filesz<=len(raw) and flags and align==4
 assert va%align==0 and va==pa and va+memsz<=0x500000
 segments.append(dict(virtual_address=hex(va),physical_address_field=hex(pa),file_offset=hex(offset),file_bytes=filesz,memory_bytes=memsz,flags=flags,alignment=align))
for a,b in zip(segments,segments[1:]):assert int(a['virtual_address'],16)+a['memory_bytes']<=int(b['virtual_address'],16)
span=max(int(s['virtual_address'],16)+s['memory_bytes'] for s in segments)
assert all('qcom,x1e80100' in (P/'upstream'/n).read_text() for n in ['camss-icp.c','camss-ipe.c'])
assert 'qcom_mdt_load' in (P/'upstream/camss-icp.c').read_text()
assert 'ELFCLASS32' in (P/'oem/a5_core.c').read_text() and '"CAMERA_ICP.elf"' in (P/'oem/a5_core.c').read_text()
report=dict(stage=352,upstream_commit='ebd1e440443121d18f730ab2aeea5586a754f36f',
 upstream_primary_url='https://kernel.googlesource.com/pub/scm/linux/kernel/git/bod/linux/+/ebd1e440443121d18f730ab2aeea5586a754f36f',
 pinned_prototype_missing_makefile_sources=missing,pinned_prototype_ipe_not_in_makefile=True,
 ipe_session_api_definitions_missing_from_fetched_sources=missing_ipe_apis,
 pinned_prototype_not_ready_to_build_or_deploy_as_is=True,only_one_icp_bps_ipe_named_upstream_head_observed=True,
 register_differences=registers,prototype_loader='MDT/PAS on X1E80100',target_loader='ELF32 ARM A5 into firmware IOVA window',
 target_firmware_segments=segments,target_firmware_entry=entry,target_firmware_runtime_span=span,
 downstream_firmware_iova_window_start=0,downstream_firmware_iova_window_bytes=0x500000,
 firmware_fits_original_window=True,no_camera_named_reserved_region_observed_in_current_dt=True,
 reserved_region_absence_not_a_proof_dynamic_allocation_impossible=True,
 hfi_queue_layout_actual_firmware_evidence='firmware-queue-validation.json',
 no_firmware_boot_or_new_hardware_driver_yet=True,
 next_required_work=['A5-specific CSR/doorbell and firmware-loader backend','ICP IOMMU streams and firmware/shared buffer mappings','HFI queues and session lifecycle','IPE IO/IQ command preparation and libcamera m2m integration'],passed=True)
(HERE/'icp-reuse-assessment.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(missing_sources=missing,missing_ipe_api_count=len(missing_ipe_apis),runtime_span=span,firmware_window=0x500000,register_contracts_compared=len(registers),passed=True),indent=2))
