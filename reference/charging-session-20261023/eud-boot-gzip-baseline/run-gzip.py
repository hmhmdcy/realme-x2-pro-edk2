"""One original gzip -c baseline; no FV rebuild, header patching or boot output."""
from pathlib import Path
import hashlib,json,os,stat,struct,subprocess,sys,traceback,zlib

own=Path(__file__).resolve().parent
previous=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/eud-boot-compact-baseline-private-01')
private=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/eud-boot-gzip-baseline-private-01')
manifest_path=own.parent/'eud-boot-packaging-review/inspection.json'
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(manifest_path.read_bytes())=='2caa68c513fd7503e0357aa4eb392594c906c82133c6e8d5d1fd3c3e703a3b87'
m=json.loads(manifest_path.read_text())
assert sha((previous/'result.json').read_bytes())=='c81ae504e6bf89253dea83a0f5a6831dd7084ade73ab23d45d22f976c9c1467b'
prior=json.loads((previous/'result.json').read_text());assert prior['passed'] and prior['full_FD_byte_equal']
tool=next(t for t in m['tools'] if Path(t['path']).name=='gzip')
assert sha(Path(tool['path']).read_bytes())==tool['sha256']
boot_path=Path(m['rollback']['path']);boot=boot_path.read_bytes();assert sha(boot)==m['rollback']['sha256']
ks,rs,ss,page,version=[struct.unpack_from('<I',boot,p)[0] for p in [8,16,24,36,40]]
assert (rs,ss,page,version)==(1,0,2048,1)
align=lambda n,a:(n+a-1)//a*a
payload=boot[page:page+ks];d=zlib.decompressobj(31);oldraw=d.decompress(payload)+d.flush()
assert d.eof and not d.unconsumed_tail
compat=d.unused_data;oldgzip=payload[:-len(compat)]
assert sha(compat)==m['android']['compat_sha256'] and sha(oldgzip)==m['android']['gzip_sha256']
ramdisk=boot[page+align(ks,page):page+align(ks,page)+rs]
id_hash=hashlib.sha1()
for p in [payload,ramdisk]:id_hash.update(p);id_hash.update(struct.pack('<I',len(p)))
id_hash.update(struct.pack('<II',0,0))
assert boot[576:608]==id_hash.digest()+b'\0'*12,'old Android ID must pass before gzip'
fd=(previous/'compact.fd').read_bytes();assert sha(fd)==m['saved_compact_FD']['sha256']
raw=oldraw[:144]+fd;assert raw==oldraw and sha(raw)==m['android']['raw_sha256']
paths={Path(p) for p in prior['inputs_before']}
paths.update([previous/'result.json',previous/'compact.fd',manifest_path,Path(__file__),Path(tool['path'])])
def snap():return {str(p):sha(p.read_bytes()) for p in sorted(paths)}
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def run():
    assert not private.exists(),'unique directory exists; no replay'
    before=snap();mount_before=Path('/proc/self/mountinfo').read_bytes()
    assert all(before[p]==digest for p,digest in prior['inputs_before'].items()),'previous frozen parent input changed'
    private.mkdir(parents=True)
    result={'passed':False,'scope':'original a30 gzip+compat baseline only; no boot or candidate',
            'host_linux_pid':os.getpid(),'old_Android_ID_verified_before_tool':True,'raw_byte_equal_a30':True,
            'raw_sha256':sha(raw),'inputs_before':before,'argv':[tool['path'],'-c'],
            'compact_private_result_sha256':sha((previous/'result.json').read_bytes())}
    print(json.dumps({'started':True,'host_linux_pid':os.getpid(),'private_directory':str(private)}),flush=True)
    try:
        path=private/'raw.bin';path.write_bytes(raw)
        stamp=m['android']['gzip_mtime'];os.utime(path,ns=(stamp*10**9,stamp*10**9))
        env=dict(os.environ,PATH='/usr/bin:/bin');env.pop('GZIP',None)
        with path.open('rb') as source,(private/'raw.gz').open('wb') as output,(private/'stderr.log').open('wb') as err:
            st=os.fstat(source.fileno());assert stat.S_ISREG(st.st_mode) and st.st_size==7340176 and st.st_mtime_ns//10**9==1792719172
            result['stdin_fstat']={'regular_file':True,'bytes':st.st_size,'mtime_ns':st.st_mtime_ns,'inode':st.st_ino,'device':st.st_dev,'mode':oct(st.st_mode)}
            write(private/'result.json',result)
            done=subprocess.run(result['argv'],stdin=source,stdout=output,stderr=err,env=env,cwd=private,timeout=120)
        result['tool_returncode']=done.returncode;assert done.returncode==0
        actual=(private/'raw.gz').read_bytes()
        result['actual_gzip_sha256']=sha(actual);result['actual_gzip_bytes']=len(actual)
        result['actual_header_hex']=actual[:10].hex();result['expected_header_hex']=oldgzip[:10].hex()
        result['gzip_byte_equal_a30']=actual==oldgzip
        assert result['gzip_byte_equal_a30'],'any gzip/header byte difference is failure'
        combined=actual+compat;result['payload_byte_equal_a30']=combined==payload
        result['payload_sha256']=sha(combined);result['payload_bytes']=len(combined)
        assert result['payload_byte_equal_a30'],'any payload byte difference is failure'
        (private/'kernel.payload').write_bytes(combined);result['passed']=True
    except BaseException as exc:result['error']=repr(exc);result['traceback']=traceback.format_exc()
    finally:
        result['inputs_after']=snap();result['parent_inputs_unchanged']=before==result['inputs_after']
        result['parent_mountinfo_unchanged']=mount_before==Path('/proc/self/mountinfo').read_bytes()
        result['passed'] &= result['parent_inputs_unchanged'] and result['parent_mountinfo_unchanged']
        result['evidence']={p.name:sha(p.read_bytes()) for p in private.iterdir() if p.is_file() and p.name!='result.json'}
        write(private/'result.json',result)
        public={k:v for k,v in result.items() if k not in ['inputs_before','inputs_after','traceback']}
        public['parent_input_count']=len(before);public['private_result_sha256']=sha((private/'result.json').read_bytes())
        public['executed_runner_sha256']=sha(Path(__file__).read_bytes());write(own/'result.json',public);print(json.dumps(public,indent=2))
    return 0 if result['passed'] else 1
if __name__=='__main__':
    if sys.argv[1:]==['--execute-gzip-baseline']:raise SystemExit(run())
    elif sys.argv[1:] in [[],['--check-local']]:print(json.dumps({'checked':True,'execution':False,'private_exists':private.exists(),'Android_ID_verified':True,'raw_byte_equal':True}))
    else:raise SystemExit('use --check-local or separately authorized --execute-gzip-baseline')
