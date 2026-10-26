"""Offline OV02A1B mode/control evidence. No device, SDK or build operations."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import math
import os
import re
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('constraints_storage449',HERE.parent/'kernel449/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
BUILD=storage.mount.mounted_build()
SOURCE=BUILD.parent/'source354'
P=Path('/mnt/e/edk2-samurai-out')
OUT=P/'kernel458';OUT.mkdir(mode=0o700,parents=True,exist_ok=True)
COMMIT='9f17f1b568626b393e785b369c5dc94543774d7a'
REPO=Path('/home/cy122/x2pro-linux/refs/CamxChi-k117')

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(name,value): (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def frozen_inputs():
    files=[p for stage in ['kernel453','kernel454'] for p in (HERE.parent/stage).iterdir() if p.is_file()]
    return {str(p.relative_to(HERE.parent)):sha(p) for p in sorted(files)}

def sources():
    names=['Documentation/userspace-api/media/v4l/ext-ctrls-image-source.rst',
           'Documentation/userspace-api/media/v4l/ext-ctrls-image-process.rst',
           'Documentation/driver-api/media/camera-sensor.rst',
           'drivers/media/i2c/imx290.c','drivers/media/i2c/imx335.c','drivers/media/i2c/imx415.c',
           'drivers/media/i2c/ov02a10.c','drivers/media/i2c/imx471.c',
           'drivers/media/v4l2-core/v4l2-ctrls-defs.c','drivers/media/v4l2-core/v4l2-fwnode.c',
           'drivers/media/v4l2-core/v4l2-common.c',
           'Documentation/userspace-api/media/drivers/camera-sensor.rst',
           'drivers/media/platform/qcom/camss/camss.c','drivers/media/platform/qcom/camss/camss-csiphy.c']
    manifest=[]
    folder=OUT/'linux-sources';folder.mkdir(exist_ok=True)
    for name in names:
        path=SOURCE/name
        if path.exists():
            raw=path.read_bytes();(folder/name.replace('/','--')).write_bytes(raw)
            manifest.append(dict(path=name,sha256=sha(path),bytes=len(raw)))
    write('linux-source-manifest-private.json',dict(source=str(SOURCE),head=subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD']).decode().strip(),files=manifest))
    pinned=[]
    for name in ['camx/src/core/camximagesensordata.h','chi-cdk/api/sensor/camxsensordriver.xsd',
                 'camx/src/swl/sensor/camxsensornode.cpp','camx/src/swl/sensor/camximagesensorutils.cpp']:
        cached=P/'kernel117/CamxChi'/name
        result=subprocess.run(['git','-C',str(REPO),'show',COMMIT+':'+name],capture_output=True,env=dict(os.environ,GIT_NO_LAZY_FETCH='1'))
        if result.returncode:
            if not cached.is_file():
                pinned.append(dict(path=name,available=False))
                continue
            raw=cached.read_bytes()
        else: raw=result.stdout
        expected=subprocess.check_output(['git','-C',str(REPO),'rev-parse',COMMIT+':'+name],env=dict(os.environ,GIT_NO_LAZY_FETCH='1')).decode().strip()
        assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==expected
        (OUT/(Path(name).name+'-private')).write_bytes(raw)
        pinned.append(dict(path=name,available=True,git_blob_sha1=expected,sha256=hashlib.sha256(raw).hexdigest()))
    write('pinned-source-manifest-private.json',dict(commit=COMMIT,files=pinned))
    schema=ET.parse(OUT/'camxsensordriver.xsd-private').getroot()
    types={n.attrib.get('name'):n for n in schema if n.tag.endswith('complexType')}
    selected={name:ET.tostring(node,encoding='unicode') for name,node in types.items()
              if re.search('(?i)Exposure|AEC|Integration|SensorDriverData|ResolutionData',name or '')}
    write('selected-schema-types-private.json',selected)
    print(json.dumps(dict(kernel_sources=len(manifest),selected_schema_types=list(selected))),flush=True)

def decode():
    tree=ast.parse((HERE.parent/'kernel450/inspect-lens-scope.py').read_text())
    node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Description')
    scope=dict(Path=Path,struct=struct)
    exec(compile(ast.Module(body=[node],type_ignores=[]),'retained450-description','exec'),scope)
    binary=P/'kernel282/shine-ov02a1b-module-private.bin'
    assert sha(binary)=='63e2122a9b0003ed8af6eade006e3a5ef7c40beb530fa0d5a6069836e9b3b5fa'
    d=scope['Description'](binary)
    data=[]
    for name in ['sensorDriverData','resolutionInfo']:
        uid,raw=d.one(name)
        words=d.words(uid)
        data.append(dict(name=name,uid=uid,words=[dict(index=i,u64=n,double=struct.unpack('<d',struct.pack('<Q',n))[0]) for i,n in enumerate(words)]))
    write('original-structure-private.json',dict(entries=d.entries,structures=data))
    print(json.dumps(dict(description_verified=True,sensor_words=len(data[0]['words']),resolution_words=len(data[1]['words']))),flush=True)

def description():
    tree=ast.parse((HERE.parent/'kernel450/inspect-lens-scope.py').read_text())
    node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Description')
    scope=dict(Path=Path,struct=struct)
    exec(compile(ast.Module(body=[node],type_ignores=[]),'retained450-description','exec'),scope)
    return scope['Description'](P/'kernel282/shine-ov02a1b-module-private.bin')

def parser_machine():
    tree=ast.parse((HERE.parent/'kernel453/inspect-af-individual.py').read_text())
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['machine','reserve']]
    scope=dict(HERE=HERE,Path=Path,struct=struct,sys=sys,importlib=importlib)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'retained-parser-infrastructure','exec'),scope)
    native,m=scope['machine']()
    return m,lambda size:scope['reserve'](m,size)

def native_parse():
    d=description();m,reserve=parser_machine()
    table=reserve(32);entries=reserve(len(d.entries)*88);payloads=reserve(len(d.raw))
    m.u.mem_write(payloads,d.raw);m.u.mem_write(table,struct.pack('<I',len(d.entries)))
    m.u.mem_write(table+16,struct.pack('<Q',entries));root_entry=None
    for i,(uid,entry) in enumerate(d.entries.items()):
        at=entries+i*88
        m.u.mem_write(at,struct.pack('<QI',table,uid));m.u.mem_write(at+12,entry['name'].encode()+b'\0')
        m.u.mem_write(at+45,struct.pack('<Q',1));m.u.mem_write(at+68,struct.pack('<IQQ',entry['size'],payloads+d.base+entry['offset'],0))
        if entry['name']=='sensorDriverData':root_entry=at;root_size=entry['size']
    prototype=reserve(128);m.u.mem_write(prototype+16,b'sensorDriverData\0');m.u.mem_write(prototype+56,struct.pack('<Q',1))
    result=m.call(0x18ac58,prototype,0,root_entry,8,phase='native-SensorDriverDataClass-Parse')
    assert result and m.read64(root_entry+80)==root_size
    raw=bytes(m.u.mem_read(result,m.allocations[result]));(OUT/'native-sensor-struct-private.bin').write_bytes(raw)
    proof=dict(parser_entry='0x18ac58',root_payload_consumed_fully=True,struct_bytes=len(raw),struct_sha256=hashlib.sha256(raw).hexdigest(),
               description_sha256=hashlib.sha256(d.raw).hexdigest(),instructions=m.instructions,providers=m.providers)
    write('native-parser-proof-private.json',proof)
    for label,begin,end in [('native-sensor-root-loader',0x18ae68,0x19153c),('native-line-readout',0x4f41a8,0x4f42a0)]:
        disassembly=subprocess.run(['aarch64-linux-gnu-objdump','-d','-C',f'--start-address={begin}',f'--stop-address={end}',str(P/'kernel281/camera.qcom.so-private')],capture_output=True,check=True)
        (OUT/(label+'-private.asm')).write_bytes(disassembly.stdout)
    print(json.dumps(dict(native_parser_passed=True,root_bytes=root_size,struct_bytes=len(raw),instructions=m.instructions)),flush=True)
    return m,reserve,result,d,proof


def native_fields():
    m,reserve,result,d,proof=native_parse()
    base=result+88
    u32=lambda a:m.read32(a)
    u64=lambda a:m.read64(a)
    f64=lambda a:struct.unpack('<d',m.u.mem_read(a,8))[0]
    resinfo=u64(base+232);mode_count=u32(resinfo+12);modes=u64(resinfo+24)
    fields=dict(max_analog_gain=f64(base+240),max_digital_gain=f64(base+248),
                min_analog_gain_present=bool(u32(base+256)),min_analog_gain_native_storage=f64(base+264),
                vertical_offset=u32(base+272),max_line_count=u32(base+276),
                min_line_count_present=bool(u32(base+280)),min_line_count=u32(base+288),
                professional_exposure_present=bool(u32(base+292)),digital_gain_factor=f64(base+312))
    # These offsets are independently checked against the actual parser stores,
    # the serialized symbol payloads, and the line-readout function loads below.
    mode=dict(line_length_counter=u32(modes+24),frame_length_lines=u32(modes+28),
              min_horizontal_blanking=u32(modes+32),min_vertical_blanking=u32(modes+36),
              output_pixel_clock=u32(modes+40),horizontal_binning=u32(modes+44),
              vertical_binning=u32(modes+48),frame_rate=f64(modes+56),lane_count=u32(modes+64),
              integration_info_present=bool(u32(modes+88)))
    ri=d.words(d.one('resolutionInfo')[0]);mw=d.words(ri[3]);root=d.words(d.one('sensorDriverData')[0])
    assert mode_count==ri[2]==1
    for key,index in [('line_length_counter',3),('frame_length_lines',4),('min_horizontal_blanking',5),
                      ('min_vertical_blanking',6),('output_pixel_clock',7),('horizontal_binning',8),
                      ('vertical_binning',9),('lane_count',11),('integration_info_present',16)]:
        assert mode[key]==mw[index],key
    assert mode['frame_rate']==struct.unpack('<d',struct.pack('<Q',mw[10]))[0]
    assert fields['vertical_offset']==root[46] and fields['max_line_count']==root[47]
    assert fields['min_line_count_present']==root[48] and fields['min_line_count']==d.words(root[49])[0]
    assert not fields['min_analog_gain_present'] and not mode['integration_info_present']
    for key,index in [('max_analog_gain',42),('max_digital_gain',43),('digital_gain_factor',52)]:
        assert fields[key]==struct.unpack('<d',struct.pack('<Q',root[index]))[0]
    assert fields['min_analog_gain_present']==root[44] and d.payload(root[45])==b''
    assert fields['professional_exposure_present']==root[50] and d.payload(root[51])==b''
    assert d.payload(mw[17])==b''
    stream=u64(modes+16);sw=d.words(mw[2])
    stream_values={key:u32(stream+i*4) for i,key in enumerate(['virtual_channel','data_type','x_start','y_start','width','height','bit_width','stream_type'])}
    assert list(stream_values.values())==list(sw)
    assert u32(modes+8)==mw[1]==1 and u32(modes)==mw[0]
    write('native-field-layout-private.json',dict(base_bytes=88,fields=fields,mode_count=mode_count,mode=mode,
          stream=stream_values,color_filter_arrangement=u32(modes),
          resinfo_hex=bytes(m.u.mem_read(resinfo,32)).hex(),mode_hex=bytes(m.u.mem_read(modes,216)).hex()))
    from unicorn.arm64_const import UC_ARM64_REG_D0
    old=m.instructions
    m.call(0x4f41a8,resinfo,0,0,phase='actual-native-line-readout')
    actual=struct.unpack('<d',struct.pack('<Q',m.u.reg_read(UC_ARM64_REG_D0)))[0]
    vt=int(mode['line_length_counter']*mode['frame_length_lines']*mode['frame_rate'])
    model=(mode['line_length_counter']&0xffff)*1e9/vt
    assert actual==model
    write('native-clock-proof-private.json',dict(entry='0x4f41a8',inputs_from_full_actual_native_parser=True,
          compiler_specialized_entry_not_a_guessed_public_method_abi=True,indices=[0,0],
          actual_line_time_ns=actual,model_line_time_ns=model,nominal_vt_hz=vt,
          nominal_frame_time_ns=actual*mode['frame_length_lines'],instructions=m.instructions-old,
          physical_clock_or_link_frequency_proven=False,passed=True))
    print(json.dumps(dict(native_fields=True,native_line_readout_equal=True,mode_count=mode_count)),flush=True)


def audit(frozen_before=None):
    """Check cached original evidence and mathematical contracts; never deploy."""
    load=lambda p:json.loads(Path(p).read_text())
    d=description();layout=load(OUT/'native-field-layout-private.json')
    fields=layout['fields'];mode=layout['mode'];stream=layout['stream']
    clock=load(OUT/'native-clock-proof-private.json');native=load(OUT/'native-parser-proof-private.json')
    assert native['root_payload_consumed_fully'] and clock['passed'] and layout['mode_count']==1
    assert sha(P/'kernel281/camera.qcom.so-private')=='e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde'
    receipts={name:load(HERE.parent/'kernel454'/name) for name in
              ['control-validation.json','firmware-validation.json','firmware-c-validation.json','source-validation.json','mux-validation.json']}
    assert all(v['passed'] for v in receipts.values())
    control=receipts['control-validation.json']
    assert control['native_gain_quantization_vectors']==135 and control['native_fill_and_actual_c_vectors_equal']==498
    sensor_so=P/'kernel115/vendor-camera-modules/com.qti.sensor.ov02a1b.so'
    assert sha(sensor_so)==control['sensor_library_sha256']
    gain_vectors=load(P/'kernel454/native-gain-vectors-private.json')
    assert len(gain_vectors)==control['native_gain_quantization_vectors']
    f32=lambda n:struct.unpack('<f',struct.pack('<f',n))[0]
    # Extract only the three pure arithmetic assignments from the frozen
    # already-validated model, without importing its compiling/replay entry.
    old_tree=ast.parse((HERE.parent/'kernel454/replay-controls.py').read_text())
    loop=next(n for n in old_tree.body if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='value')
    assignments=[n for n in loop.body if isinstance(n,ast.Assign) and all(isinstance(t,ast.Name) for t in n.targets)
                 and n.targets[0].id in ['scale','quantized','register']]
    assert [n.targets[0].id for n in assignments]==['scale','quantized','register']
    arithmetic=compile(ast.Module(body=assignments,type_ignores=[]),'frozen454-pure-gain-arithmetic','exec')
    factors={row['register']/row['analog'] for row in gain_vectors}
    assert len(factors)==1
    gain_factor=factors.pop()
    def gain_model(gain):
        scope=dict(gain=gain)
        exec(arithmetic,scope)
        code=scope['register'];analog=code/gain_factor
        return code,analog,f32(gain/analog)
    for row in gain_vectors:
        code,analog,residual=gain_model(row['real_gain'])
        assert (code,analog,residual)==(row['register'],row['analog'],row['isp'])
    # Derive the stock callback's finite code lattice from the already-proven
    # model. No claim that every encoding-only raw code is a stock gain step.
    callback_min=min(row['analog'] for row in gain_vectors)
    lattice=sorted({gain_model(code/gain_factor)[0] for code in range(int(callback_min*gain_factor),int(fields['max_analog_gain']*gain_factor)+1)})
    assert all(gain_model(code/gain_factor)[0]==code for code in lattice)
    fill_vectors=load(P/'kernel454/native-control-vectors-private.json')
    assert len(fill_vectors)==control['native_fill_and_actual_c_vectors_equal']
    packed=fill_vectors[0]['registers'];page_addr,page_value=packed[:2]
    tables=load(P/'kernel454/firmware-tables-private.json')['tables']
    bank=None;registers={}
    for table in tables[:3]:
        for address,value,delay in table:
            if address==page_addr:bank=value
            else:registers[(bank,address)]=value
    initial=lambda idx:(registers[(page_value,packed[idx])]<<8)|registers[(page_value,packed[idx+2])]
    encoding_base=control['frame_base_in_register_units']
    initial_controls=dict(frame_length_lines=initial(2)+encoding_base,exposure_lines=initial(6),
       analog_register=registers[(page_value,packed[10])],table_reconstruction_only_not_physical_readback=True)
    width,height=stream['width'],stream['height'];nominal=mode['frame_length_lines']
    margin=fields['vertical_offset'];min_exp=fields['min_line_count'];max_exp=min(fields['max_line_count'],nominal-margin)
    assert mode['line_length_counter']<width and mode['output_pixel_clock']!=clock['nominal_vt_hz']
    assert nominal>=height+mode['min_vertical_blanking']
    assert min_exp<=max_exp<nominal and not mode['integration_info_present']
    assert min_exp<=initial_controls['exposure_lines']<=max_exp
    assert initial_controls['analog_register'] in lattice
    assert initial_controls['frame_length_lines']!=nominal
    # Frame-period data alone underdetermines the pixel-array unit conversion.
    # These are algebraic counterexamples, never selectable clock candidates.
    scales=[math.ceil(width/mode['line_length_counter']),math.ceil(width/mode['line_length_counter'])+1]
    ambiguity=[dict(algebra_only_not_a_clock_candidate=True,scale=k,
         hblank_pixels=k*mode['line_length_counter']-width,pixel_rate=k*clock['nominal_vt_hz']) for k in scales]
    assert all(row['hblank_pixels']>=0 and math.isclose(
         (width+row['hblank_pixels'])/row['pixel_rate'],mode['line_length_counter']/clock['nominal_vt_hz']) for row in ambiguity)
    # This is an intentionally fixed nominal-mode mathematical policy, not a
    # recovered OEM maximum frame-length policy or a hardware safety claim.
    accepts=lambda frame,exposure:frame==nominal and min_exp<=exposure<=min(fields['max_line_count'],frame-margin)
    valid=[(nominal,min_exp),(nominal,max_exp),(nominal,(min_exp+max_exp)//2)]
    invalid=[(nominal,min_exp-1),(nominal,max_exp+1),(nominal-1,min_exp),(nominal+1,min_exp),(0,0)]
    assert all(accepts(*v) for v in valid) and not any(accepts(*v) for v in invalid)
    cpp=(P/'kernel454/camximagesensordata.cpp-private').read_text()
    header=(OUT/'camximagesensordata.h-private').read_text()
    linux=OUT/'linux-sources'
    hmax=(linux/'drivers--media--i2c--imx415.c').read_text()
    helper=(linux/'drivers--media--v4l2-core--v4l2-common.c').read_text()
    camss=(linux/'drivers--media--platform--qcom--camss--camss.c').read_text()
    source_checks={
      'vt_uses_counter_frame_rate':'pResData->lineLengthPixelClock * pResData->frameLengthLines * pResData->frameRate' in cpp,
      'line_time_uses_vt':'(lineLengthPixelClock * NanoSecondsPerSecond) / VTPixelClock' in cpp,
      'frame_ceiling_uses_tuning_min_fps':'GetMaxFPS(resolutionIndex) / GetMinFPS(resolutionIndex, cameraID)' in cpp and 'GetMaxExposureData' in cpp,
      'csiphy_budget_uses_output_clock':'outputPClk * bitWidth' in cpp and 'pCmdCSIPHYConfig->laneCount' in cpp and 'overrideOPPCLOCK' in cpp,
      'min_line_count_is_explicit':'m_pSensorData->exposureControlInfo.minLineCount' in header,
      'raw_hmax_conversion_example':'IMX415_HMAX_MULTIPLIER' in hmax and '(format->width + ctrl->val) /' in hmax,
      'link_freq_bus_config_preferred':'if (mbus_config.link_freq)' in helper,
      'link_freq_control_then_pixel_rate_estimate':'V4L2_CID_LINK_FREQ' in helper and 'Link frequency estimated using pixel rate' in helper,
      'camss_keeps_array_and_transport_distinct':'V4L2_CID_PIXEL_RATE describes the sensor array' in camss and 'frequency = camss_get_link_freq' in camss,
    }
    assert all(source_checks.values()),source_checks
    constraints=dict(deployable=False,supplier='Shine',module='OV02A1B mono',
       original_description_sha256=sha(P/'kernel282/shine-ov02a1b-module-private.bin'),sensor_library_sha256=sha(sensor_so),
       fields=fields,mode=mode,stream=stream,nominal_timing=clock,table_initial_controls=initial_controls,
       table_frame_differs_from_mode_metadata=True,
       must_apply_selected_frame_exposure_gain_after_init_mode_before_actual_stream_on=True,
       frame_period_does_not_prove_pixel_units=ambiguity,
       provenance=dict(
         min_line_count=dict(serialized='sensorDriverData[48] presence; [49] payload',native='root+280 presence, +288 value'),
         vertical_offset=dict(serialized='sensorDriverData[46]',native='root+272'),
         max_line_count=dict(serialized='sensorDriverData[47]',native='root+276'),
         max_analog_gain=dict(serialized='sensorDriverData[42] double',native='root+240'),
         min_analog_gain=dict(serialized='sensorDriverData[44] absent; [45] empty',native='root+256 absent; +264 zero is not a gain minimum'),
         integration_info=dict(serialized='resolutionData[16] absent; [17] empty',native='mode+88 absent'),
         line_length_counter=dict(serialized='resolutionData[3]',native='mode+24'),
         nominal_frame_length=dict(serialized='resolutionData[4]',native='mode+28'),
         output_pixel_clock=dict(serialized='resolutionData[7] uint32',native='mode+40 uint32'),
         nominal_frame_rate=dict(serialized='resolutionData[10] double',native='mode+56 double'),
         gain_lattice=dict(source='frozen454 actual calculate callback model and cached 135 native vectors',
                          sensor_entry=control['calculate_callback']),
         initial_controls=dict(source='frozen454 tables replayed in page order; addresses from actual cached fill vectors',
                               no_device_readback=True)),
       first_window_mathematical_policy=dict(frame_length_lines=nominal,vblank_lines=nominal-height,
          exposure_min_lines=min_exp,exposure_max_lines=max_exp,write_granularity_lines=1,
          stock_integration_time_step_field_present=False,stock_frame_ceiling_recovered=False,
          proposed_policy_not_hardware_verified=True),
       analogue_gain=dict(raw_code_lattice=lattice,real_gain_by_index=[c/gain_factor for c in lattice],
          proposed_v4l2_units='integer index into this documented lattice; custom userspace gain mapping required',
          model_rechecked_cached_native_vectors=len(gain_vectors),sensor_digital_gain_fixed=fields['max_digital_gain'],
          isp_residual_is_not_sensor_digital_gain=True),
       output_clock_consumer=dict(budget_only_output_clock_hz=mode['output_pixel_clock'],
          bits_per_pixel=stream['bit_width'],lanes=mode['lane_count'],
          fixed_source_zero_override_data_rate_bps=mode['output_pixel_clock']*stream['bit_width']//mode['lane_count'],
          actual_override_or_physical_dphy_rate_not_recovered=True),
       missing=['physical MCLK/PLL proof','counter-to-array-pixel conversion','physical D-PHY UI/link_freq',
          'actual mode AE min-FPS/frame ceiling','hardware endpoint/control timing checks'],
       source_checks=source_checks,valid_contract_vectors=valid,rejected_contract_vectors=invalid)
    write('mode-control-contract-private.json',constraints)
    if frozen_before is not None:
        assert frozen_before==frozen_inputs(),'Frozen 453/454 input changed during offline audit'
    public=dict(stage=458,scope='offline cached source/native-parser control and timing constraints',
       passed=True,deployable=False,no_phone_sdk_build_or_deployment=True,
       input_sha256=dict(description=constraints['original_description_sha256'],sensor_library=sha(sensor_so),
          hal=sha(P/'kernel281/camera.qcom.so-private'),schema=sha(OUT/'camxsensordriver.xsd-private'),
          fixed_chi_image_sensor_cpp=sha(P/'kernel454/camximagesensordata.cpp-private'),
          public_realme_mono=sha(P/'kernel454/ov02a1b-realme-mono-source-private.c')),
       chi_commit=COMMIT,linux_source_head=load(OUT/'linux-source-manifest-private.json')['head'],
       linux_sources=load(OUT/'linux-source-manifest-private.json')['files'],
       actual_hal_parser=dict(root_consumed_fully=True,parsed_structure_bytes=native['struct_bytes'],instructions=native['instructions'],
          serialized_and_native_mode_fields_equal=True,single_mode=True,optional_presence_checked=True),
       actual_native_line_readout=dict(entry='0x4f41a8',instructions=clock['instructions'],model_equal=True,
          uses_actual_parsed_objects=True,physical_clock_proven=False),
       reused454=dict(native_fill_vectors=498,native_gain_vectors=135,firmware_bytes=760,rerun=False,
          receipt_sha256={name:sha(HERE.parent/'kernel454'/name) for name in receipts}),
       constraints=dict(minimum_exposure_present=True,vertical_offset_present=True,max_line_count_present=True,
          integration_min_step_margin_group_absent=True,min_analog_descriptor_absent_callback_clamp_present=True,
          gain_steps_nonuniform=True,sensor_digital_gain_fixed=True,nominal_fixed_frame_policy_only=True,
          maximum_frame_policy_recovered=False,negative_hblank_rejected=True,output_clock_is_not_vt=True,
          frame_period_underdetermines_array_units=True,init_table_frame_differs_from_declared_mode=True,
          pixel_rate_or_link_frequency_selected=False,shared_pm_resources_not_integrated=True),
       mathematical_contract=dict(valid_vectors=len(valid),invalid_vectors=len(invalid),all_passed=True),
       frozen453_454_files_unchanged=frozen_before is not None,
       source_checks=source_checks,private_contract_sha256=sha(OUT/'mode-control-contract-private.json'),checker_sha256=sha(__file__))
    (HERE/'constraints-validation.json').write_text(json.dumps(public,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(passed=True,receipt='constraints-validation.json',deployable=False,cached_gain_vectors=len(gain_vectors))),flush=True)

if __name__=='__main__':
    if sys.argv[1:]==['--sources']: sources()
    elif sys.argv[1:]==['--decode']: decode()
    elif sys.argv[1:]==['--native-parse']: native_parse()
    elif sys.argv[1:]==['--native-fields']: native_fields()
    elif sys.argv[1:]==['--audit']: audit()
    elif sys.argv[1:]==['--all']:
        before=frozen_inputs()
        sources();decode();native_fields();audit(before)
        write('frozen-inputs-private.json',dict(before=before,after_equal=True))
    else: raise SystemExit('Use --sources, --decode, --native-parse, --native-fields, --audit or --all; no device operations')
