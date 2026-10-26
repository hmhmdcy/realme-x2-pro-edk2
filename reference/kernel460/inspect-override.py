"""Connect the matching configuration library to the retained HAL AF pre-clip branch."""
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
import tarfile
import xml.etree.ElementTree as ET
sys.dont_write_bytecode = True
HERE=Path(__file__).resolve().parent
P=Path('/mnt/e/edk2-samurai-out')
PRIVATE=P/'kernel460'
HAL_SHA='e2b1b9b6379507052464d9f9573c2a5a1b1cf37c43947b53645ddc8948a70dde'


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_individual_definitions(library):
    original=HERE.parent/'kernel453/inspect-af-individual.py'
    assert sha(original)=='efef4663149eef4cbcb50806ae2648e34f3c81c004246c36447232b50f3a90b0'
    tree=ast.parse(original.read_text())
    source450=ast.parse((HERE.parent/'kernel450/inspect-lens-scope.py').read_text())
    description=next(node for node in source450.body if isinstance(node,ast.ClassDef) and node.name=='Description')
    directory=PRIVATE/'individual-replay';directory.mkdir(mode=0o700,exist_ok=True)
    namespace=dict(globals(),HERE=original.parent,PRIVATE=directory,
                   HAL=P/'kernel281/camera.qcom.so-private',
                   DESCRIPTION=P/'kernel326/qtech_s5k3m5sx-description-private.bin',
                   DESCRIPTION_SHA='823404fcc1d9cf3afa4fa126ecfa456d160188e594a9defd0bf519786988bc77')
    exec(compile(ast.Module(body=[description],type_ignores=[]),'retained450-description-class','exec'),namespace)
    selected={'hal_bytes','hal_at','machine','reserve','parse_description','decode_af_descriptor','format_af'}
    definitions='\n\n'.join(ast.get_source_segment(original.read_text(),node) for node in tree.body
                              if isinstance(node,ast.FunctionDef) and node.name in selected)
    assert definitions.count('return native, IndividualMachine()')==1
    definitions=definitions.replace('return native, IndividualMachine()','return native, IndividualMachine')
    exec(compile(definitions,'retained453-functions-private-output-rebound','exec'),namespace)
    template=namespace['machine']
    def machine():
        native,base=template()
        from unicorn.arm64_const import UC_ARM64_REG_X0,UC_ARM64_REG_PC,UC_ARM64_REG_LR,UC_ARM64_REG_D0
        class WithConfiguration(base):
            def __init__(self):
                super().__init__();self.override_calls=[]
            def step(self,u,pc,size,unused):
                if pc in (0x5b1fb0,0x5b1fc0,0x5b1fd0):
                    arguments=[u.reg_read(UC_ARM64_REG_X0+i) for i in range(5)]
                    group=self.string(arguments[0]);key=self.string(arguments[1]) if pc!=0x5b1fb0 else None
                    assert group==b'OemCamActuatorSettingMap'
                    row=dict(pc=hex(pc),group=group.decode())
                    if pc==0x5b1fb0:
                        result=library.get_keys(group);row.update(api='GetKeyCount',result=result)
                    elif pc==0x5b1fc0:
                        result=library.get_count(group,key);row.update(api='GetValuesCount',key=key.decode(),result=result)
                    else:
                        locale=self.string(arguments[2]);count=arguments[4]
                        assert arguments[3] and count==4
                        result,values=library.get_list(group,key,locale,count)
                        u.mem_write(arguments[3],struct.pack('<4i',*values))
                        row.update(api='GetLocaleIntegerListConfiguration',key=key.decode(),locale=locale.decode(),count=count,result=result,values=values)
                    self.override_calls.append(row)
                    u.reg_write(UC_ARM64_REG_X0,result);u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR));return
                if pc==0x5b1730:
                    a,b,c,d,e=[u.reg_read(UC_ARM64_REG_X0+i) for i in range(5)]
                    fmt=self.string(d);assert fmt==b'%d',fmt
                    stack,grtop,vrtop,groff,vroff=struct.unpack('<QQQii',u.mem_read(e,32))
                    value=struct.unpack('<i',u.mem_read(grtop+groff if groff<0 else stack,4))[0]
                    text=str(value).encode();assert len(text)<c
                    u.mem_write(a,text+b'\0');u.reg_write(UC_ARM64_REG_X0,len(text));u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR));return
                if pc==0x5b12d0:
                    exponent=u.reg_read(UC_ARM64_REG_X0)&0xffffffff
                    if exponent & (1<<31):exponent-=1<<32
                    value=struct.unpack('<d',struct.pack('<Q',u.reg_read(UC_ARM64_REG_D0)))[0]
                    u.reg_write(UC_ARM64_REG_D0,struct.unpack('<Q',struct.pack('<d',math.ldexp(value,exponent)))[0])
                    u.reg_write(UC_ARM64_REG_PC,u.reg_read(UC_ARM64_REG_LR));return
                super().step(u,pc,size,unused)
        return native,WithConfiguration()
    namespace['machine']=machine
    return namespace


def main():
    spec=importlib.util.spec_from_file_location('storage449override',HERE.parent/'kernel449/storage.py')
    storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
    storage.mount.mounted_build()
    PRIVATE.mkdir(mode=0o700,exist_ok=True)
    assert sha(P/'kernel281/camera.qcom.so-private')==HAL_SHA
    source_dir=P/'kernel453/af-config-source'
    source=json.loads((source_dir/'source-private.json').read_text())
    settings=json.loads((source_dir/'settings-source-private.json').read_text())
    assert source['hal_matched'] and source['hal_sha256']==HAL_SHA and source['partition']=='odm'
    assert source['relative_path']=='lib64/libhwconfigurationutil.so'
    assert source['readonly_debugfs'] and not source['mounted_before'] and not source['mounted_after']
    assert settings['hal_matched'] and settings['readonly_debugfs'] and not settings['phone_files_written']
    assert settings['library_sha256']==source['sha256']
    assert settings['path']=='/odm/etc/camera/CameraHWConfiguration.config'
    spec=importlib.util.spec_from_file_location('native460',HERE/'native-config.py')
    config=importlib.util.module_from_spec(spec);spec.loader.exec_module(config)
    assert sha(source_dir/'libhwconfigurationutil-r6.so')==source['sha256']==config.LIB_SHA
    assert sha(source_dir/'CameraHWConfiguration-r6.config')==settings['sha256']==config.CONFIG_SHA
    protected=[HERE.parent/'kernel453/inspect-af-individual.py',HERE.parent/'kernel453/af-individual-validation.json',
               P/'kernel453/af-individual/s5k3m5-conditional-individual-step-candidate-private.json']
    protected += list((P/'kernel453/af-profile').glob('*candidate-private.json'))
    before={str(path):sha(path) for path in protected}
    library=config.Machine();assert library.load()
    namespace=load_individual_definitions(library)
    native,m,parsed,sensor_info,obj,formatter=namespace['format_af']()
    reserve,Description=namespace['reserve'],namespace['Description']
    from unicorn import UC_HOOK_CODE
    from unicorn.arm64_const import UC_ARM64_REG_PC,UC_ARM64_REG_SP,UC_ARM64_REG_X29,UC_ARM64_REG_W25,UC_ARM64_REG_W28
    d=Description(namespace['DESCRIPTION']);uid,payload=d.one('actuatorDriver');entry=m.description_entries[uid]
    m.u.mem_write(entry+80,bytes(8));prototype=reserve(m,128)
    m.u.mem_write(prototype+16,b'actuatorDriver\0');m.u.mem_write(prototype+56,struct.pack('<Q',1))
    module=m.call(0x1773a8,prototype,0,entry,8,phase='460-native-actuator-parser')
    assert module and m.read64(entry+80)==len(payload)
    driver=module+88;actor=reserve(m,4096);outer=reserve(m,64)
    m.u.mem_write(actor+2064,struct.pack('<Q',driver));m.u.mem_write(outer+32,struct.pack('<Q',actor))
    assert m.read32(driver+40)==0 and struct.unpack('<H',m.u.mem_read(driver+44,2))[0]==10
    region_count,regions=m.read32(driver+144),m.read64(driver+152)
    assert region_count==1
    count=struct.unpack('<H',m.u.mem_read(regions,2))[0]
    stack=0x20e0000;m.u.reg_write(UC_ARM64_REG_SP,stack);m.u.reg_write(UC_ARM64_REG_X29,stack+0x400)
    m.u.mem_write(stack+48,struct.pack('<QQ',outer,sensor_info))
    m.u.mem_write(0x96aac0,bytes(2048));m.u.mem_write(0x5bf2b0+16,bytes(4))
    pcs=[];bounds=[]
    def hook(u,pc,size,unused):
        pcs.append(pc)
        if pc==0x4f8474:
            signed=lambda value:value-(1<<32) if value&(1<<31) else value
            bounds.append(dict(lower=signed(u.reg_read(UC_ARM64_REG_W28)),upper=signed(u.reg_read(UC_ARM64_REG_W25))))
    handle=m.u.hook_add(UC_HOOK_CODE,hook)
    m.phase='460-current-library-api-through-original-hal-override-and-all-steps'
    try:
        m.u.emu_start(0x4f7e44,0x4f89cc,timeout=15000000,count=3000000)
        assert m.u.reg_read(UC_ARM64_REG_PC)==0x4f89cc
    except Exception as error:
        (PRIVATE/'hal-branch-failure-private.json').write_text(json.dumps(dict(error=repr(error),last_pcs=[hex(pc) for pc in pcs[-60:]],calls=m.override_calls),indent=2)+'\n')
        raise
    finally:m.u.hook_del(handle)
    assert len(bounds)==1
    original=json.loads(protected[2].read_text())
    actual=list(struct.unpack('<'+'h'*count,m.u.mem_read(actor,count*2)))
    assert bounds[0]==original['supplied_clip_bounds'] and actual==original['step_table']
    assert struct.unpack('<h',m.u.mem_read(driver+136,2))[0]==original['individual_initial_code']
    assert struct.unpack('<f',m.u.mem_read(regions+4,4))[0]==original['individual_code_per_step']
    assert [row['locale'] for row in m.override_calls if row['api'].startswith('GetLocale')]==['0','1']
    assert all(row['result']==0 for row in m.override_calls if row['api'].startswith('GetLocale'))
    assert all(sha(path)==digest for path,digest in before.items())
    proof=dict(hal_sha256=HAL_SHA,library_sha256=config.LIB_SHA,configuration_sha256=config.CONFIG_SHA,
               input_source_sha256=sha(source_dir/'source-private.json'),settings_source_sha256=sha(source_dir/'settings-source-private.json'),
               native_begin='0x4f7e44',native_end_exclusive='0x4f89cc',instructions=len(pcs),calls=m.override_calls,
               clip_bounds=bounds[0],step_table=actual,initial_code=original['individual_initial_code'],code_per_step=original['individual_code_per_step'],
               prior_conditional_candidate_sha256=sha(protected[2]),library_providers=library.providers,
               all_bounds_and_step_values_equal_retained453=True,protected_files_before=before,
               checksum_certified=False,static_sag_gate_verified=False,live_orientation_verified=False,optical_safety_verified=False,
               actual_android_process_environment_executed=False,deployable=False,applied=False)
    (PRIVATE/'native-hal-override-proof-private.json').write_text(json.dumps(proof,indent=2)+'\n')
    (PRIVATE/'native-hal-trace-private.json').write_text(json.dumps(dict(pcs=pcs,api_calls=m.override_calls))+'\n')
    print(json.dumps(dict(stage=460,native_hal_override_path_completed=True,locales=['0','1'],bounds_and_every_step_unchanged=True,
                          checksum_verified=False,deployable=False,instructions=len(pcs))))


if __name__=='__main__':main()
