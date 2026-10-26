"""Compare a portable composed step with complete native Execute and IPE bindings."""
from pathlib import Path
import copy,hashlib,importlib.util,json,shutil,struct,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);out=importlib.util.module_from_spec(spec);spec.loader.exec_module(out);return out
native=module('execute416',HERE/'execute-model.py').ExecuteMachine()
transport=module('binding416',HERE/'binding-model.py').BindingMachine()
tree_model=module('tree414',HERE.parent/'kernel414/tree-model.py')
gamma=(P.parent/'kernel413/target-default-gamma-private.bin').read_bytes();weights=(P.parent/'kernel413/histogram-log-weights-private.bin').read_bytes()
histograms=[bytes(4096),struct.pack('<1024I',*([64]*1024)),struct.pack('<1024I',65536,*([0]*1023))]
profiles=json.loads((P.parent/'kernel412/mode-profiles-private.json').read_text())
sdk=Path('/home/cy122/x2pro-linux/libcamera214-root');work=sdk/'private/camss416-execute'
names=['kernel416/execute-runner.cpp','kernel416/libipa/tmc_input.cpp','kernel416/libipa/tmc_input.h',
       'kernel415/libipa/tmc_runtime.cpp','kernel415/libipa/tmc_runtime.h','kernel414/libipa/tmc11_tree.cpp',
       'kernel414/libipa/tmc11_tree.h','kernel413/libipa/tmc11_generation.cpp','kernel413/libipa/tmc11_generation.h','kernel412/libipa/tmc11_ltm.h']
for name in names:
    dest=work/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE.parent/name,dest)
rels=[n for n in names if n.endswith('.cpp')];flags=['-std=c++17','-O2','-ffp-contract=fast','-Wall','-Wextra','-Werror']
binary=P/'execute-host';q=subprocess.run(['g++',*flags,'-fsanitize=address,undefined','-no-pie',*[str(HERE.parent/n) for n in rels],'-o',str(binary)],capture_output=True);assert not q.returncode,q.stderr.decode()
def tree_bytes(root,triggers):
    raw=struct.pack('<2I5fI',*root['control_method'],triggers[0],triggers[2],triggers[3],triggers[4],triggers[5],len(root['core']))
    for d in root['core']:
        raw+=struct.pack('<2fI',*d['trigger'],len(d['children']))
        for h in d['children']:
            raw+=struct.pack('<6fI',*h['trigger'],len(h['children']))
            for a in h['children']:raw+=struct.pack('<4f',*a['trigger'])+tree_model.region_bytes(a['data'])
    return raw
records=[];gold=[];actual_host=[];cases=[];calculated=0;stale_version=0;missing=0
for variant,contexts in profiles.items():
    for context in contexts:
        base=context['modules']['tmc11_sw'];tmc10=context['modules']['tmc10_sw'];native.reset()
        old_policy=bytes(56);old_adrc=bytes(4236);old_cache=bytes(4236);old_hist=0;selected=None
        native_cache=bytes(4236)
        steps=[([2,1.2,2,140,3,4],0,[0,0],1,'initial'),
               ([2,1.2,2,140,3,4],0,[0,0],2,'hist-only'),
               ([2,1.2,2,140,3,4],1,[0,0],2,'force-equal'),
               ([2,1.2,2,180,3,4],0,[1,1],2,'locked-update'),
               ([2,1.2,2,180,3,4],0,[0,0],0,'unlock-equal'),
               ([2,1.2,2,180,3,4],1,[0,0],0,'force-retained-hist'),
               ([4,2,3,210,3,4],0,[0,0],0,'missing-property'),
               ([4,2,3,210,3,4],0,[0,0],0,'disable-new-uid'),
               ([4,2,3,210,3,4],0,[0,0],0,'restore-new-uid'),
               ([4,2,3,210,3,4],2,[0,0],1,'same-uid-flipped-enable'),
               ([4,2,3,210,3,8],0,[0,0],1,'sensitivity-ratio-change')]
        for step,(triggers,force,locks,hp,kind) in enumerate(steps):
            candidate=copy.deepcopy(base)
            if step==7:candidate['uid']+=10000;candidate['enabled']=0
            elif step>=8:
                candidate['uid']+=10001
                if step==9:candidate['enabled']=1-candidate['enabled']
            triggers=list(struct.unpack('<6f',struct.pack('<6f',*triggers)))
            old_words=struct.unpack_from('<8I',old_policy);old_triggers=struct.unpack_from('<6f',old_policy,32)
            if selected is None or candidate['uid']!=selected['uid']:selected=candidate
            words=[candidate['uid'],candidate['enabled'],old_words[7],int(step!=0),old_words[0],force,*locks,int(hp!=0),int(old_hist!=0)]
            policy_input=struct.pack('<10I12f',*words,*old_triggers,*triggers)
            reserve=selected['reserve'];property_present=kind!='missing-property';missing+=not property_present
            raw=policy_input+struct.pack('<5I',reserve['use_gtm'],reserve['use_ltm'],reserve['curve_model'],reserve['curve_order'],property_present)
            raw+=gamma+weights+histograms[hp]+histograms[old_hist]+old_adrc+old_cache
            raw+=struct.pack('<3I',1,tmc10['enabled'],tmc10['reserve']['use_ltm'])+tree_bytes(selected,triggers)
            record=struct.pack('<I',len(raw))+raw
            q=subprocess.run([str(binary)],input=record,capture_output=True,timeout=15);assert not q.returncode,q.stderr.decode();assert len(q.stdout)==8548
            assert struct.unpack_from('<I',q.stdout)[0]==1
            body=q.stdout[4:];ported_policy=body[:56];ported_adrc=body[56:4292];ported_cache=body[4292:8528]
            target=native.request(candidate,triggers,force,locks,hp);assert target['gamma']==gamma
            native_cache,_=transport.metadata(target['adrc'] if property_present else None,native_cache)
            cache_version=struct.unpack_from('<I',native_cache,4)[0];binding,_=transport.binding(cache_version,0)
            request_version=struct.unpack_from('<I',binding)[0];ltm_enable=struct.unpack_from('<I',native_cache,12)[0]
            decision,_=transport.ltm(struct.pack('<7I',1,tmc10['enabled'],tmc10['reserve']['use_ltm'],request_version,1,ltm_enable,0))
            wanted=struct.pack('<I',1)+target['policy']+target['adrc']+native_cache+binding[:4]+decision
            assert len(wanted)==8548
            records.append(record);gold.append(wanted);actual_host.append(q.stdout)
            diff=sum(a!=b for a,b in zip(q.stdout,wanted));assert not diff,(variant,context['usecase'],step,kind,diff)
            calc=struct.unpack_from('<I',ported_policy,8)[0];calculated+=calc
            producer_version=struct.unpack_from('<I',target['policy'],4)[0];property_version=struct.unpack_from('<I',target['adrc'],4)[0]
            stale_version+=producer_version!=property_version
            cases.append(dict(variant=variant,uid=candidate['uid'],context=context['usecase'],mode=context['sensor_mode_index'],
                step=kind,calculated=bool(calc),hist_token=target['hist_token'],producer_version=producer_version,
                property_version=property_version,ipe_request_version=request_version,original_instructions=target['instructions']))
            old_policy=ported_policy;old_adrc=ported_adrc;old_cache=ported_cache
            source=struct.unpack_from('<I',ported_policy,24)[0]
            if source==2:old_hist=hp
            elif source==0:old_hist=0
            assert old_hist==target['hist_token']
        print('complete native sequence',variant,context['sensor_mode_index'],context['usecase'],flush=True)
inputs=b''.join(records);expected=b''.join(gold);actual=b''.join(actual_host)
(P/'execute-input-private.bin').write_bytes(inputs);(P/'execute-target-private.bin').write_bytes(expected)
(P/'execute-host-actual-private.bin').write_bytes(actual);(P/'execute-cases-private.json').write_text(json.dumps(cases,indent=2)+'\n')
binary_arm='/private/camss416-execute/execute-aarch64'
q=subprocess.run(['chroot',str(sdk),'g++',*flags,*['/private/camss416-execute/'+n for n in rels],'-o',binary_arm],capture_output=True);assert not q.returncode,q.stderr.decode()
q=subprocess.run(['chroot',str(sdk),binary_arm],input=inputs,capture_output=True,timeout=45);assert not q.returncode,q.stderr.decode()
(P/'execute-aarch64-actual-private.bin').write_bytes(q.stdout);assert q.stdout==expected,('arm',sum(a!=b for a,b in zip(q.stdout,expected)))
report=dict(stage=416,ordinary_mode_contexts=sum(len(v) for v in profiles.values()),physical_sensor_variants=len(profiles),
    complete_execute_calls=len(records),steps_per_context=11,calculated_requests=calculated,
    synthetic_missing_property_cases=missing,module_version_differs_from_retained_property_version_cases=stale_version,
    complete_original_execute_entry='0x383728',original_returned_success_each_time=True,existing_adrc_storage_no_allocator_provider=True,
    original_execute_instructions=native.instructions,original_execute_providers=native.providers,
    original_transport_binding_consumer_instructions=transport.instructions,original_transport_binding_consumer_providers=transport.providers,
    actual_module_state_adrc4236_ipe_cache_binding_and_ltm_gate_checked=True,
    locked_cache_updates_hist_only_force_and_disabled_retained_output_checked=True,
    selected_factory_roots_and_arrays_unchanged_synthetic_uid_enable_variants_explicit=True,
    original_compiled_gamma_each_request_verified=True,statistics_two_explicit_immutable_buffers_synthetic=True,
    logf_expf_powf_host_libm_not_bionic=True,portable_single_process_composed_step=True,
    architectures=[dict(architecture=a,cases=len(records),compared_bytes=len(expected),different_bytes=0,passed=True) for a in ['host','aarch64']],
    current_source_hashes=[dict(path=n,sha256=hashlib.sha256((HERE.parent/n).read_bytes()).hexdigest()) for n in names],
    camera_root_selector_not_executed_again=True,real_ife_publish_or_ipe_whole_execute_not_executed=True,
    phone_accessed=False,android_runtime_metadata_observed=False,product_request_integration=False,
    last_device_evidence_stage=406,full_goal_kept_active=True,passed=True)
(HERE/'execute-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
