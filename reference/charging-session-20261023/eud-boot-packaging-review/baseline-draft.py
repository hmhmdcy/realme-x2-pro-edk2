"""Default: check-local only. --execute-baseline requires separate explicit approval."""
from pathlib import Path
import hashlib,json,lzma,os,re,struct,subprocess,sys,traceback,uuid,zlib

own=Path(__file__).resolve().parent
manifest_path=own/'inspection.json'
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(manifest_path.read_bytes())=='2caa68c513fd7503e0357aa4eb392594c906c82133c6e8d5d1fd3c3e703a3b87'
m=json.loads(manifest_path.read_text())
private=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/eud-boot-pack-baseline-private-01')
parser=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel104/verify-firmware.py')
assert sha(parser.read_bytes())=='2e0b03aa3cf7ae7651e0b2e1153c1c5eb0cba3a3b41ef1d375c9b06358cb9d5d'
scope={};exec(compile(parser.read_text().split('\ndt_audit=',1)[0],str(parser)+':definitions-only','exec'),scope)
fv,sections,align=scope['fv'],scope['sections'],scope['align']
inputs=[m[k] for k in ['rollback','saved_main_FV','saved_compact_FD','candidate_EFI','candidate_native_DTB']]
inputs += [m[k]['config'] for k in ['main_config','compact_config']]+m['tools']+m['source_rules']
inputs += m['main_config']['inputs']+m['compact_config']['inputs']
repo=Path('/home/cy122/edk2-samurai/repo')
shared=repo/'workspace/Build/samurai/RELEASE_GCC5'
parent_paths=[repo/'boot-samurai.img']+[shared/'FV'/n for n in ['FVMAIN.Fv','FVMAIN_COMPACT.Fv','SM8150_UEFI.fd','SM8150_UEFI.fd-bootshim']]
parent_paths += [repo/'Platform/RenegadePkg/Library/PlatformBootManagerLib'/n for n in ['PlatformBm.c','PlatformBm.h','PlatformBootManagerLib.inf']]
parent_paths += [shared/'AARCH64/MdeModulePkg/Universal/BdsDxe/BdsDxe'/n for n in ['GNUmakefile','DEBUG/BdsDxe.dll','OUTPUT/BdsDxe.efi']]
for p in parent_paths:inputs.append({'path':str(p),'sha256':sha(p.read_bytes())})
tools={Path(t['path']).name:t['path'] for t in m['tools']}
main_guid=m['main_FV']['filesystem_guid'];outer_guid=m['compact_FV']['filesystem_guid']
container_guid='9E21FD93-9C72-4C15-8C4B-E77F1DB2D792';sec_guid='8af09f13-44c5-96ec-1437-dd899cb5ee5d'
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def snapshot():return {i['path']:sha(Path(i['path']).read_bytes()) for i in inputs}
def unpack():
    boot=Path(m['rollback']['path']).read_bytes();assert sha(boot)==m['rollback']['sha256']
    ks=m['android']['kernel_payload_bytes'];page=m['android']['page'];payload=boot[page:page+ks]
    d=zlib.decompressobj(31);raw=d.decompress(payload)+d.flush();compat=d.unused_data
    assert d.eof and not d.unconsumed_tail and sha(compat)==m['android']['compat_sha256']
    gz=payload[:-len(compat)];assert sha(gz)==m['android']['gzip_sha256']
    assert gz[:10].hex()==m['android']['gzip_header_hex'] and gz[3]==0 # FLG0: no FNAME/FEXTRA/FHCRC
    fd=raw[144:];outer=fv(fd);container=next(v for v in outer.values() if v['type']==0xb)
    _,body,sec=container['sections'][0];offset=struct.unpack_from('<H',body,16)[0]
    decoded=lzma.decompress(sec[offset:],format=lzma.FORMAT_ALONE);main=sections(decoded)[0][1]
    assert sha(main)==m['saved_main_FV']['sha256'] and sha(fd)==m['saved_compact_FD']['sha256']
    ramdisk=boot[page+align(ks,page):page+align(ks,page)+1]
    h=hashlib.sha1()
    for value in [payload,ramdisk]:h.update(value);h.update(struct.pack('<I',len(value)))
    h.update(struct.pack('<II',0,0)) # absent second and absent v1 recovery_dtbo
    assert boot[576:608]==h.digest()+b'\0'*12,'old Android ID mismatch; no tool may run'
    return {'boot':boot,'payload':payload,'gzip':gz,'raw':raw,'shim':raw[:144],'fd':fd,'main':main,'compat':compat,'decoded':decoded,'compressed':sec[offset:]}
def extract(volume,items,directory):
    result={}
    for item in items:
        data=bytearray(volume[item['offset']:item['offset']+item['bytes']])
        assert sha(data)==item['sha256'] and data[23]==0xf8
        head=bytearray(data[:item['header_size']]);head[17]=head[23]=0;assert sum(head)%256==0
        data[23]^=0xff
        head=bytearray(data[:item['header_size']]);head[17]=head[23]=0;assert sum(head)%256==0
        assert sha(data)==item['standalone_sha256']
        path=directory/(item['guid']+'.ffs');path.write_bytes(data);result[item['guid']]=path
    return result
def inf(config,values,out):
    text=Path(config['path']).read_text();ordered=iter(values)
    text=re.sub(r'^EFI_FILE_NAME\s*=.*$',lambda _: 'EFI_FILE_NAME = '+str(next(ordered)),text,flags=re.M)
    assert next(ordered,None) is None
    out.write_text(text)
def command_plan():
    p=private
    return [
      [tools['GenFv'],'-g',main_guid,'-i',str(p/'FVMAIN.inf'),'-o',str(p/'main.Fv')],
      [tools['GenSec'],'-s','EFI_SECTION_FIRMWARE_VOLUME_IMAGE','-o',str(p/'main.fv.sec'),str(p/'main.Fv')],
      [tools['GenSec'],'--sectionalign','8','-o',str(p/'main.aligned'),str(p/'main.fv.sec')],
      [tools['LzmaCompress'],'-e','-o',str(p/'main.lzma'),str(p/'main.aligned')],
      [tools['GenSec'],'-s','EFI_SECTION_GUID_DEFINED','-g',m['compression']['guided_guid'],'-r','PROCESSING_REQUIRED','-o',str(p/'main.guided'),str(p/'main.lzma')],
      [tools['GenFfs'],'-t','EFI_FV_FILETYPE_FIRMWARE_VOLUME_IMAGE','-g',container_guid,'-o',str(p/'container.ffs'),'-i',str(p/'main.guided')],
      [tools['GenFv'],'-g',outer_guid,'-F','FALSE','-i',str(p/'FVMAIN_COMPACT.inf'),'-o',str(p/'compact.fd')],
      [tools['gzip'],'-c']]
def check():
    actual=snapshot()
    assert all(actual[i['path']]==i['sha256'] for i in inputs)
    original=unpack()
    return original,actual
def execute():
    assert not private.exists(),'unique directory exists; no replay'
    original,before=check();private.mkdir(parents=True);(private/'inputs').mkdir()
    result={'passed':False,'scope':'old a30 packaging baseline only; no candidate or boot.img','commands':[],
            'host_linux_pid':os.getpid(),'Android_ID_verified_before_tools':True,'inputs_before':before,'manifest_sha256':sha(manifest_path.read_bytes())}
    print(json.dumps({'baseline_started':True,'host_linux_pid':os.getpid(),'private_directory':str(private)}),flush=True)
    try:
        inner=extract(original['main'],m['main_FV']['files'],private/'inputs')
        outer=extract(original['fd'],m['compact_FV']['files'],private/'inputs')
        inf(m['main_config']['config'],[inner[i['guid']] for i in m['main_FV']['files']],private/'FVMAIN.inf')
        inf(m['compact_config']['config'],[outer[sec_guid],private/'container.ffs'],private/'FVMAIN_COMPACT.inf')
        expected=[original['main'],original['decoded'],original['decoded'],original['compressed'],None,
                  outer[container_guid.lower()].read_bytes(),original['fd'],original['gzip']]
        outputs=['main.Fv','main.fv.sec','main.aligned','main.lzma','main.guided','container.ffs','compact.fd','raw.gz']
        for index,argv in enumerate(command_plan()):
            if index==7:
                raw=original['shim']+(private/'compact.fd').read_bytes()
                assert raw==original['raw'];(private/'raw.bin').write_bytes(raw)
                stamp=m['android']['gzip_mtime'];os.utime(private/'raw.bin',ns=(stamp*10**9,stamp*10**9))
            entry={'argv':argv,'stdout_file':outputs[index]+'.stdout','stderr_file':outputs[index]+'.stderr'}
            result['commands'].append(entry);write(private/'result.json',result)
            env=dict(os.environ,PATH='/usr/bin:/bin');env.pop('GZIP',None)
            with (private/entry['stderr_file']).open('wb') as err:
                if index==7:
                    with (private/'raw.bin').open('rb') as source,(private/'raw.gz').open('wb') as output:
                        st=os.fstat(source.fileno());entry['stdin']={'type':'regular file redirected to fd0','path':str(private/'raw.bin'),'mtime_ns':st.st_mtime_ns}
                        done=subprocess.run(argv,stdin=source,stdout=output,stderr=err,env=env,cwd=private,timeout=120)
                else:
                    with (private/entry['stdout_file']).open('wb') as out:
                        done=subprocess.run(argv,stdout=out,stderr=err,env=env,cwd=private,timeout=120)
            entry['returncode']=done.returncode;write(private/'result.json',result);assert done.returncode==0
            data=(private/outputs[index]).read_bytes();entry['sha256']=sha(data);entry['bytes']=len(data)
            if index==4:
                expected_guided=next(v for v in fv(original['fd']).values() if v['type']==0xb)['sections'][0][2]
                assert data==expected_guided
            else:assert data==expected[index],'baseline byte difference at '+outputs[index]
            entry['byte_equal_reference']=True
        rebuilt_payload=(private/'raw.gz').read_bytes()+original['compat']
        assert rebuilt_payload==original['payload'];(private/'kernel.payload').write_bytes(rebuilt_payload)
        result['payload_sha256']=sha(rebuilt_payload);result['passed']=True
    except BaseException as exc:result['error']=repr(exc);result['traceback']=traceback.format_exc()
    finally:
        result['inputs_after']=snapshot();result['parent_inputs_unchanged']=before==result['inputs_after'];result['passed'] &= result['parent_inputs_unchanged']
        result['output_hashes']={p.name:sha(p.read_bytes()) for p in private.iterdir() if p.is_file() and p.name!='result.json'}
        write(private/'result.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ['commands','inputs_before','inputs_after','traceback','output_hashes']}
                     | {'stages':[{'output':outputs[i],'returncode':x.get('returncode'),'byte_equal_reference':x.get('byte_equal_reference',False)} for i,x in enumerate(result['commands'])]},indent=2))
    return 0 if result['passed'] else 1

if __name__=='__main__':
    if sys.argv[1:] in [[],['--check-local']]:
        check();print(json.dumps({'checked':True,'packing_executed':False,'private_directory_exists':private.exists(),'planned_commands':command_plan()},indent=2))
    elif sys.argv[1:]==['--execute-baseline']:raise SystemExit(execute())
    else:raise SystemExit('only --check-local (default) or separately approved --execute-baseline')
