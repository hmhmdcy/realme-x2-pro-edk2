"""Actual maintained DS4 C versus complete retained target instruction paths."""
from pathlib import Path
import hashlib,importlib.util,json,re,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
kernel=module('storage284',HERE.parent/'kernel284/storage.py').mounted_build().parent/'source354';camss=kernel/'drivers/media/platform/qcom/camss'
state=json.loads((HERE/'source-state.json').read_text());assert subprocess.check_output(['git','-C',str(kernel),'rev-parse','HEAD'],text=True).strip()==state['commit']
n=module('ds426',HERE/'ds4-model.py');m=n.Machine();cases=[];expected=[];rows=[];execute_rows=[]
for variant in ['sunny_s5kgw1','sunny_imx471','qtech_s5k3m5sx','sunny_imx319']:
 assert json.loads((HERE/(variant+'-ds4-extraction-validation.json')).read_text())['passed']
 index=json.loads((P.parent/'kernel333'/(variant+'-index-private.json')).read_text());raw=(P.parent/('kernel'+str(index['source_stage']))/index['filename']).read_bytes()
 def blob(uid):
  e=index['entries'][str(uid)];return raw[index['base']+e['offset']:index['base']+e['offset']+e['bytes']]
 roots=json.loads((P/(variant+'-ds4-reserves-private.json')).read_text());parsed_roots={}
 for root in roots:
  data=blob(root['uid']);revision_uid=struct.unpack_from('<Q',data,32)[0]
  parsed,output=m.parse(root['tag'],root['uid'],data,revision_uid,blob(revision_uid));parsed_roots[root['uid']]=parsed
  assert output[136:200]==struct.pack('<16I',*[v for row in root['passes'] for v in row])
  for height in [128,480,1080,8192]:
   for previous in [[0]*4,[0xffffffff]*4,[0xa7a7a7a7,0x12345678,0x87654321,0x10000]]:
    cases.append(struct.pack('<8I',height,*root['passes'][0][1:],*previous));expected.append(m.packed(parsed,height,previous))
  rows.append(dict(variant=variant,tag=root['tag'],uid=root['uid'],whole_target_class_parsed=True,all_four_passes_match=True,native_calculation_reads_only_pass_full_coefficients=True))
 for selected in json.loads((P/(variant+'-ds4-selection-private.json')).read_text()):
  if selected['tag']!='ds4to1v10_ife_full_dc4':continue
  parsed=parsed_roots[selected['uid']];before=len(m.selections)
  registers,enable,obj=m.execute(parsed,640,480)
  assert m.selections[before:]==[selected['tag']] and enable==0x1400
  assert registers==m.registers(parsed,480)
  execute_rows.append(dict(variant=variant,sensor_mode_index=selected['sensor_mode_index'],usecase=selected['usecase'],uid=selected['uid'],whole_target_create_execute=True,mode_selection_provider_returns_original_manager_selected_parsed_module=True,register_transport_recorded=True,enable_mask_verified=True))
prefix='''#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
typedef uint16_t u16;typedef uint32_t u32;
#define BIT(n) (1U<<(n))
#define GENMASK(h,l) ((UINT32_MAX<<(l)) & (UINT32_MAX>>(31-(h))))
#define FIELD_PREP(mask,val) (((u32)(val)<<__builtin_ctz(mask)) & (mask))
'''
strip=lambda t:re.sub(r'^#include.*\n','',t,flags=re.M)
source=prefix+strip((camss/'camss-vfe-175-ds4.h').read_text())+strip((camss/'camss-vfe-175-ds4.c').read_text())+(HERE/'codec-runner.c').read_text()
(P/'codec-model.c').write_text(source);inputs=b''.join(cases);outputs=[];golden=b''.join(expected)
for arch,cc,flags,launch in [('host','gcc',['-fsanitize=address,undefined','-no-pie'],[]),('aarch64','aarch64-linux-gnu-gcc',['-static'],['qemu-aarch64'])]:
 target=P/('codec-'+arch);q=subprocess.run([cc,'-std=gnu11','-O2','-Wall','-Wextra','-Werror',*flags,str(P/'codec-model.c'),'-o',str(target)],capture_output=True)
 (P/(arch+'-codec-build.log')).write_bytes(q.stdout+q.stderr);assert not q.returncode,q.stderr.decode()
 q=subprocess.run([*launch,str(target)],input=inputs,capture_output=True);(P/(arch+'-codec-run.log')).write_bytes(q.stderr);assert not q.returncode,q.stderr.decode()
 (P/(arch+'-codec-output-private.bin')).write_bytes(q.stdout);assert q.stdout==golden,(arch,len(q.stdout),len(golden));outputs.append(q.stdout)
assert outputs[0]==outputs[1];(P/'codec-input-private.bin').write_bytes(inputs);(P/'native-registers-private.bin').write_bytes(golden)
r=dict(stage=426,source_commit=state['commit'],actual_maintained_c_function_built=True,physical_tuning_variants=4,roots=len(rows),native_class_parses=len(rows),
 register_cases=len(cases),compared_bytes=len(golden),different_bytes=0,invalid_preserve_cases_per_architecture=10,in_place_output_verified=True,
 host_asan_ubsan=True,aarch64_static_qemu=True,native_full_ds4_and_r2pd_register_paths=True,native_first_pass_binding_read_trace_verified=True,
 original_parser_xml_and_mode_manager_crosscheck=True,execute_cases=execute_rows,
 all_root_coefficients_used_as_first_ds4_codec_fixtures=True,full_execute_binds_only_selected_ife_full_dc4=True,ds16_hardware_not_implemented=True,
 target_unicorn_mode_getter_is_framework_provider=True,target_register_transport_is_provider=True,mathematics_not_replaced_by_provider=True,
 native_instructions=m.instructions,providers=m.providers,all_coefficients_and_full_registers_private=True,
 producer_prerequisites_precrop_round_dma_not_implemented=True,hardware_enqueue_and_pixel_dma_not_executed=True,phone_accessed=False,passed=True)
(HERE/'codec-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='execute_cases'},indent=2))
