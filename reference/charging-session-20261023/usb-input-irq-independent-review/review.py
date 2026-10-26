"""Independent static/hash review only. No author entrypoint/test/build invoked."""
from pathlib import Path
import hashlib,json,re,struct
H=Path(__file__).resolve().parent
R=H.parents[1]
A=R/'charging-oem-audit-20261023/usb-input-irq-candidate'
O=R/'charging-oem-audit-20261023/apsd-lifecycle/oem/arch--arm64--boot--dts--19781--pm8150b.dtsi'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
d=json.loads((A/'delivery.json').read_bytes())
assert sha(A/'delivery.json')=='392ba7974a8ed76151e4a320d0a1cb226c300612ef5e01ca7ff983a60d539c5d'
assert d['frozen'] and d['actual_cases']==16
for n,v in d['files'].items():assert sha(A/n)==v['sha256'] and (A/n).stat().st_size==v['bytes'],n
c=(A/'samurai-usb-input.c').read_text();old=(A/'baseline-samurai-usb-input.c').read_text()
def fn(text,n):
 pos=text.index(n+'(');start=text.rfind('\n',0,pos)+1;i=text.index('{',pos)+1;depth=1
 while depth:depth+=(text[i]=='{')-(text[i]=='}');i+=1
 return text[start:i]
unchanged=['samurai_usb_read_status','samurai_usb_get_budget','samurai_usb_type','samurai_usb_get_property','samurai_usb_set_property','samurai_usb_poll','samurai_usb_stop','samurai_usb_suspend','samurai_usb_resume','samurai_usb_retain_for_native_consumer','samurai_usb_parent_match','samurai_usb_exit']
assert all(fn(c,n)==fn(old,n) for n in unchanged)
newnames=['samurai_usb_event','samurai_usb_request_events','samurai_usb_stop','samurai_usb_shutdown']
assert '\n'.join(fn(c,n)+'\n' for n in newnames)==(A/'actual-events-and-stop.inc').read_text()
probe=fn(c,'samurai_usb_probe')
tokens=['INIT_DELAYED_WORK','input->paused = true;','samurai_usb_request_events(pdev, input)','devm_power_supply_register','devm_add_action_or_reset(dev, samurai_usb_stop, input)','input->paused = false;','schedule_delayed_work']
assert [probe.index(x) for x in tokens]==sorted(probe.index(x) for x in tokens)
event=fn(c,'samurai_usb_event');assert event.index('mutex_lock')<event.index('if (!input->paused)')<event.index('mod_delayed_work')<event.index('mutex_unlock')
assert 'samurai_usb_stop(platform_get_drvdata(pdev));' in fn(c,'samurai_usb_shutdown')
init=fn(c,'samurai_usb_init');assert init.index('of_find_compatible_node')<init.index('if (available)')<init.index('platform_device_register_full')
t=json.loads((A/'test-result.json').read_bytes());b=json.loads((A/'build-result.json').read_bytes());rel=json.loads((A/'test-artifact-relocation.json').read_bytes())
assert t['passed'] and t['asan_ubsan'] and t['actual_function_result']['actual_function_cases']==16
for key,n in [('source_sha256','samurai-usb-input.c'),('test_source_sha256','test-events.c'),('actual_extracted_functions_sha256','actual-events-and-stop.inc'),('runner_sha256','run-tests-before-private-output.py')]:assert t[key]==sha(A/n)
assert rel['original_test_receipt_sha256']==sha(A/'test-result.json') and not rel['cases_rerun']
assert rel['old_runner_sha256']==sha(A/'run-tests-before-private-output.py') and rel['new_runner_sha256']==sha(A/'run-tests.py')
assert b['passed'] and b['returncode']==0 and b['owned_child_waited'] and b['diagnostics']==[]
assert b['source_sha256']==sha(A/'samurai-usb-input.c') and b['decoder_sha256']==sha(A/'samurai-usb-input-decode.h')
assert b['test_receipt_sha256']==sha(A/'test-result.json') and b['builder_sha256']==sha(A/'build-private-object.py')
assert '-Werror' in b['command'] and '-DKBUILD_EXTRA_WARN1' in b['command']
assert b['shared_and_original_inputs_unchanged'] and b['config_not_written'] and not b['Image_module_or_firmware_linked']
assert d['object_sha256']==b['object_sha256']
for v in b['source_references'].values():assert sha(A/'source-reference'/v['path'].split('source354/')[1].replace('/','--'))==v['sha256']==v['snapshot_sha256']

# Independently decode existing raw native FDT, not the author's output/parser.
dtb=Path('E:/edk2-samurai-out/charging-management-20261023/eud-boot-policy-private/samurai-eud-off-policy-private.dtb')
assert sha(dtb)=='9271d9cc33b3701ad0675c6345d43e9a5c404aa6c192126edc3eb715b0914358'
raw=dtb.read_bytes();hd=struct.unpack_from('>10I',raw);assert hd[0]==0xd00dfeed and hd[1]==len(raw)
st=raw[hd[3]:hd[3]+hd[8]];i=hd[2];nodes={};stack=[]
while i<hd[2]+hd[9]:
 tag=struct.unpack_from('>I',raw,i)[0];i+=4
 if tag==1:
  e=raw.index(0,i);stack.append(raw[i:e].decode());i=(e+4)&~3;nodes['/'+'/'.join(stack[1:])]={}
 elif tag==2:stack.pop()
 elif tag==3:
  size,off=struct.unpack_from('>II',raw,i);i+=8;e=st.index(0,off);nodes['/'+'/'.join(stack[1:])][st[off:e].decode()]=raw[i:i+size];i=(i+size+3)&~3
 elif tag==4:pass
 elif tag==9:break
 else:raise RuntimeError(tag)
sp='/soc@0/spmi@c440000';pm=sp+'/pmic@2'
assert nodes[sp]['compatible']==b'qcom,spmi-pmic-arb\0' and 'interrupt-controller' in nodes[sp]
assert nodes[sp]['#interrupt-cells']==struct.pack('>I',4)
assert nodes[pm]['reg']==struct.pack('>II',2,0) and b'qcom,pm8150b\0' in nodes[pm]['compatible']
assert not {'interrupt-parent','#interrupt-cells'}&nodes[pm].keys()
assert nodes[pm]['#address-cells']==struct.pack('>I',1) and nodes[pm]['#size-cells']==struct.pack('>I',0)
assert nodes[pm+'/typec@1500']['status']==b'disabled\0'
assert not any(b'realme,rmx1931-usb-input\0' in p.get('compatible',b'') for p in nodes.values())
o=O.read_text();block=o[o.index('qcom,usb@1300'):o.index('qcom,dc@1400')]
block=re.sub(r'/\*.*?\*/|//[^\n]*','',block,flags=re.S)
specs=re.findall(r'<(0x2) (0x13) (0x[0-7]) (IRQ_TYPE_EDGE_\w+)>',block)
names=re.findall(r'"([^"]+)"',block[block.index('interrupt-names'):])
mapping=dict(zip(names,[list(x) for x in specs]));assert mapping['usbin-plugin']==['0x2','0x13','0x4','IRQ_TYPE_EDGE_BOTH']
assert mapping['usbin-src-change']==['0x2','0x13','0x6','IRQ_TYPE_EDGE_RISING']

out=dict(verdict='no_new_blocker_in_reviewed_scope',author_delivery_sha256=sha(A/'delivery.json'),source_sha256=sha(A/'samurai-usb-input.c'),baseline_sha256=sha(A/'baseline-samurai-usb-input.c'),decoder_sha256=sha(A/'samurai-usb-input-decode.h'),
 test_receipt_sha256=sha(A/'test-result.json'),build_receipt_sha256=sha(A/'build-result.json'),relocation_sha256=sha(A/'test-artifact-relocation.json'),
 native_DTB_sha256=sha(dtb),native_PMIC_interrupt_parent_and_cells_absent=True,native_PMIC_address_cells=1,native_PMIC_size_cells=0,native_existing_custom_input_count=0,
 oem_source_sha256=sha(O),oem_IRQ_mapping={n:mapping[n] for n in ['usbin-plugin','usbin-src-change']},
 unchanged_functions={n:hashlib.sha256(fn(c,n).encode()).hexdigest() for n in unchanged},
 author_test_scope='16 cases, four actual functions, pthread/fake IRQ and work boundaries; no rerun',
 author_build_scope='one AArch64 W1/Werror object, receipt and retained source bindings verified; not rebuilt',
 lifecycle='paused before IRQ request; supply/action before unpause; locked event check+queue; stop unlocks before join; shutdown calls same stop; stop action before supply/IRQ/input devres',
 fallback_1s_unchanged=True,active_single_DT_node_suppresses_software_provider=True,
 normal_IRQ_controller_programming_not_charger_APSD_policy_write=True,
 limits=['Fragment not compiled/applied; no actual IRQ allocation/delivery or latency acceptance.','Optional platform lookup can collapse non-defer discovery errors to ENXIO; fallback is not IRQ success.','Duplicate suppression is for the intended single matching enabled board node.','OS IRQ/work/devres full implementation and physical PM/shutdown concurrency are not fixture evidence.'],
 actions=dict(author_files_modified=False,tests_run=False,build_run=False,device_accessed=False,SDK_invoked=False,storage_guard_or_mount_used=False),
 reviewer_source_sha256=sha(Path(__file__)))
(H/'review-result.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(dict(verdict=out['verdict'],review_sha256=sha(H/'review-result.json'))))
