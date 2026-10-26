"""Read existing carrier/ELF/source inputs only. No tools/build/packing/mount/device."""
from pathlib import Path
import hashlib,json,lzma,re,shlex,shutil,struct,sys,uuid,zlib
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
PRIVATE=Path('/mnt/e/edk2-samurai-out')
CH=PRIVATE/'charging-management-20261023'
NEW=Path('/home/cy122/charging-management-20261023/gauge-image501-B-repro-01')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=NEW/'source354'
boot=CH/'eud-boot-two-ffs-candidate-private-01/boot-two-ffs-private.img'
logdump=PRIVATE/'kernel365/logdump-k365-candidate-private.img'
dtb=CH/'eud-boot-policy-private/samurai-eud-off-policy-private.dtb'
efi=CH/'eud-bds-r2-private-01/BdsDxe/OUTPUT/BdsDxe.efi'
image=NEW/'build/arch/arm64/boot/Image'
oldimage=PRIVATE/'kernel363/Image-k363-private'
inputs={'boot4126':(boot,'4126a2978bc79b5cb95b6e1b86bb432a6b16ece627776237c163b93b323bbfcf'),
        'logdumpACA':(logdump,'aca01bc2c91928f1a6a6690f62d14db014351ec5049e5684590b40c3c93de8da'),
        'nativeDTB':(dtb,'9271d9cc33b3701ad0675c6345d43e9a5c404aa6c192126edc3eb715b0914358'),
        'R2_BDS_EFI':(efi,'a0e30c69b91f5605c07136f3f0c6900434f99d72159c5c61ac01db47fc061768'),
        'Image501':(image,'3a656c75d3b714153d77b637654c894a0418fd688cc906d59a37a41401e8cc02'),
        'rollback_Image363':(oldimage,'15746aab311eed32478cdee4e13c1677716ff48c8a04316c9c15cf606c9d6468')}
for p,d in inputs.values():assert sha(p)==d
parser=REF/'kernel104/verify-firmware.py'
assert sha(parser)=='2e0b03aa3cf7ae7651e0b2e1153c1c5eb0cba3a3b41ef1d375c9b06358cb9d5d'
scope={};exec(compile(parser.read_text().split('\ndt_audit=',1)[0],str(parser)+':definitions-only','exec'),scope)
fv,sections,align=scope['fv'],scope['sections'],scope['align']
raw=boot.read_bytes();assert len(raw)==100663296 and raw[:8]==b'ANDROID!'
ks=struct.unpack_from('<I',raw,8)[0];payload=raw[2048:2048+ks]
decoder=zlib.decompressobj(31);expanded=decoder.decompress(payload)+decoder.flush()
assert decoder.eof and len(expanded)==7340176
fd=expanded[144:];outer=fv(fd);container=next(v for v in outer.values() if v['type']==0xb)
typ,body,section=container['sections'][0];assert typ==2
offset=struct.unpack_from('<H',body,16)[0]
main=sections(lzma.decompress(section[offset:],format=lzma.FORMAT_ALONE))[0][1]
files=fv(main);assert len(files)==101
ds=files['25462cda-221f-47df-ac1d-259cfaa4e326']['sections']
bs=files['6d33944a-ec75-4855-a54d-809c75241f6c']['sections']
assert len(ds)==1 and ds[0][0]==0x19 and ds[0][1]==dtb.read_bytes()
assert next(s[1] for s in bs if s[0]==0x10)==efi.read_bytes()
nodes=scope['fdt_nodes'](dtb.read_bytes())
decode=lambda b:b.rstrip(b'\0').decode()
chosen=decode(nodes['/chosen']['bootargs'])
machine=nodes['/']['compatible'].split(b'\0');assert b'realme,samurai' in machine
gauge=[n for n,v in nodes.items() if b'ti,bq28z610' in v.get('compatible',b'').split(b'\0')]
assert len(gauge)==1
eud={n:{k:decode(v[k]) for k in ['compatible','status'] if k in v} for n,v in nodes.items() if b'eud' in v.get('compatible',b'')}
platform=REF/'charging-oem-audit-20261023/eud-boot-policy-r2/PlatformBm.c.candidate'
text=platform.read_text();found=re.search(r'STATIC CHAR16\s+mSamuraiLinuxCmdLine\[\]\s*=\s*L"([^"]+)";',text)
assert found and found[1]==chosen
prefix='bq27xxx_battery'
config=(NEW/'build/.config').read_text().splitlines()
assert 'CONFIG_BATTERY_BQ27XXX=y' in config and 'CONFIG_BATTERY_BQ27XXX_I2C=y' in config and 'CONFIG_CMDLINE=""' in config
cmd=(NEW/'build/drivers/power/supply/.bq27xxx_battery.o.cmd').read_text().splitlines()[0]
argv=shlex.split(cmd.split(' := ',1)[1]);assert '-DMODULE' not in argv
modname=next(v for v in argv if v.startswith('-DKBUILD_MODNAME='))
assert modname.split('=',1)[1].strip('"')==prefix
parameter=prefix+'.samurai_instant_current=1'
assert (prefix+'.samurai_instant_current\0').encode() in (NEW/'build/drivers/power/supply/bq27xxx_battery.o').read_bytes()
assert 'module_param(samurai_instant_current, bool, 0444);' in (source/'drivers/power/supply/bq27xxx_battery.c').read_text()
assert not any(parameter.split('=')[0] in t for t in chosen.split())
assert not any(t.startswith(('earlycon=eud','console=eud')) for t in chosen.split())
windows={'drivers/firmware/efi/libstub/fdt.c':[(84,95)],'drivers/firmware/efi/libstub/efi-stub.c':[(115,150)],
         'drivers/firmware/efi/libstub/efi-stub-helper.c':[(333,342),(401,412)],'include/linux/moduleparam.h':[(1,45)]}
source_evidence={}
for name,ranges in windows.items():
    p=source/name;lines=p.read_text().splitlines()
    source_evidence[name]={'sha256':sha(p),'lines':[{'line':i,'text':lines[i-1]} for a,b in ranges for i in range(a,min(b,len(lines))+1)]}
r2=json.loads((REF/'charging-session-20261023/eud-bds-r2-build/result.json').read_bytes())
assert r2['passed'] and len(r2['child']['libraries_after'])==41
lib_suffix='/PlatformBootManagerLib/OUTPUT/PlatformBootManagerLib.lib'
unchanged=[r for r in r2['child']['libraries_after'] if not r['path'].endswith(lib_suffix)]
assert len(unchanged)==40
old_libs={r['path']:r for r in r2['child']['libraries_after']}
unavailable=[r['path'] for r in unchanged if not Path(r['path']).is_file()]
assert not unavailable
assert all(sha(Path(r['path']))==r['sha256'] for r in unchanged)
edk_inputs={n:{'path':str(CH/'eud-bds-r2-private-01'/n),'sha256':sha(CH/'eud-bds-r2-private-01'/n)}
            for n in ['source/PlatformBm.c','PlatformBootManagerLib/OUTPUT/PlatformBm.obj',
                      'PlatformBootManagerLib/OUTPUT/PlatformBootManagerLib.lib','BdsDxe/DEBUG/BdsDxe.dll','BdsDxe/OUTPUT/BdsDxe.efi']}
tools=json.loads((REF/'charging-session-20261023/eud-boot-packaging-review/inspection.json').read_bytes())['tools']
for r in tools:assert sha(Path(r['path']))==r['sha256']
extra=[]
for name in ['mcopy','mdir','fsck.fat']:
    p=shutil.which(name);assert p
    extra.append({'name':name,'path':p,'sha256':sha(Path(p))})
result={'status':'read-only plan inputs checked; no carrier generated','inputs':{n:{'path':str(p),'bytes':p.stat().st_size,'sha256':d} for n,(p,d) in inputs.items()},
        'boot':{'main_modules':len(files),'native_DTB_matches9271':True,'BDS_PE_matches_R2':True,'kernel_payload_bytes':ks,
                'used_bytes':2048+align(ks,2048)+2048,'tail_limit':6686720},
        'native_chosen_bootargs':chosen,'planned_LoadOptions':chosen+' '+parameter,'parameter':parameter,
        'parameter_prefix_evidence':{'builtin_core':True,'builtin_i2c':True,'KBUILD_MODNAME':prefix,
                                    'command_sha256':sha(NEW/'build/drivers/power/supply/.bq27xxx_battery.o.cmd'),
                                    'full_parameter_string_in_actual_object':True},
        'gauge_node':gauge[0],'machine_compatible':[v.decode() for v in machine if v], 'EUD_nodes':eud,
        'EFI_stub_source_evidence':source_evidence,'R2_PlatformBm_source_sha256':sha(platform),
        'R2_existing_four_commands':r2['child']['commands'],'R2_private_inputs':edk_inputs,
        'other40_libraries_checked_unchanged':unchanged,'packing_tools':tools,'FAT_tools':extra,
        'rootfs_R8_camera_modified':False,'tools_executed':False,'new_carrier_or_DTB_generated':False,
        'build_mount_device_SDK_Git':False,'source_sha256':sha(Path(__file__))}
(HERE/'inputs.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':result['status'],'only_planned_partitions':['boot','logdump'],
                  'new_commandline':result['planned_LoadOptions'],'native_DTB_preserved':result['inputs']['nativeDTB'],
                  'other40_libraries_match':len(unchanged),'FAT_tools':extra},indent=2),flush=True)
