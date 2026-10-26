"""One compact-only old-a30 baseline, using original SEC rebase path. No boot or gzip."""
from pathlib import Path
import hashlib,json,os,re,shutil,struct,subprocess,sys,traceback

own=Path(__file__).resolve().parent
workspace=Path('/mnt/e/RealmeX2Pro edk2')
repo=Path('/home/cy122/edk2-samurai/repo')
previous=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/eud-boot-pack-baseline-private-01')
private=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/eud-boot-compact-baseline-private-01')
manifest_path=own.parent/'eud-boot-packaging-review/inspection.json'
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(manifest_path.read_bytes())=='2caa68c513fd7503e0357aa4eb392594c906c82133c6e8d5d1fd3c3e703a3b87'
m=json.loads(manifest_path.read_text())
assert sha((previous/'result.json').read_bytes())=='b6bdaa042815759447c2d36d2fdd204644d7db73efdfb3830e9481b260e23637'
old_result=json.loads((previous/'result.json').read_text())
assert all(c['byte_equal_reference'] for c in old_result['commands'][:6]) and not old_result['passed']
guid='8AF09F13-44C5-96EC-1437-DD899CB5EE5D'
cache=repo/('workspace/Build/samurai/RELEASE_GCC5/FV/Ffs/'+guid+'Sec')
sec_files=[cache/(guid+ext) for ext in ['.ffs','.efi','.map']]
expected_digests=['da8f6b97036aa734beb08104cf07932392d52a8d56bcee629ff810afe765266c',
                  '684fc7c898ba26036ed65cda5370bfb87725c77cd828604686848c65f651388a',
                  '0cd35c90911979e0ad3662c3df4a7fc84c3f4bacf01b4c195a95f083c356a321']
for path,digest in zip(sec_files,expected_digests):assert sha(path.read_bytes())==digest
te=(cache/(guid+'Te.raw')).read_bytes()
assert struct.unpack_from('<H',te,2)[0]==0xaa64 and struct.unpack_from('<Q',te,16)[0]==0
assert struct.unpack_from('<II',te,24)==(0,0),'stripped TE relocation expectation changed'
sidecar=sec_files[1].read_bytes();pe=struct.unpack_from('<I',sidecar,0x3c)[0];opt=pe+24
assert struct.unpack_from('<Q',sidecar,opt+24)[0]==0 and struct.unpack_from('<II',sidecar,opt+112+40)==(55360,64)
pdbs=[s.decode() for s in re.findall(rb'[\x20-\x7e]{8,}',te) if s.startswith(b'/home/') and s.endswith(b'.dll')]
assert len(pdbs)==1,'ambiguous SEC PDB path'
pdb_map=Path(pdbs[0]).with_suffix('.map');assert pdb_map.is_file()
tool=next(t for t in m['tools'] if Path(t['path']).name=='GenFv')
assert sha(Path(tool['path']).read_bytes())==tool['sha256']
container=previous/'container.ffs'
assert sha(container.read_bytes())==next(f['standalone_sha256'] for f in m['compact_FV']['files'] if f['guid'].startswith('9e21'))
reference=Path(m['saved_compact_FD']['path']);expected=reference.read_bytes();assert sha(expected)==m['saved_compact_FD']['sha256']
sec=next(f for f in m['compact_FV']['files'] if f['guid']==guid.lower())
paths={Path(p) for p in old_result['inputs_before']}
paths.update(sec_files+[cache/(guid+'Te.raw'),pdb_map,previous/'result.json',container,reference,manifest_path,
                       repo/'Common/edk2/BaseTools/Source/C/GenFv/GenFvInternalLib.c',Path(__file__)])
def snap():return {str(p):sha(p.read_bytes()) for p in sorted(paths)}
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def run():
    assert not private.exists(),'unique target exists; no replay'
    before=snap();mount_before=Path('/proc/self/mountinfo').read_bytes()
    assert all(before[p]==digest for p,digest in old_result['inputs_before'].items()),'old frozen parent input changed'
    private.mkdir(parents=True);(private/'inputs').mkdir()
    result={'passed':False,'scope':'original a30 compact-only baseline; no first6 rebuild/gzip/boot',
            'host_linux_pid':os.getpid(),'inputs_before':before,'old_failure_preserved':True,
            'original_SEC_input_sha256':expected_digests[0],'SEC_relocation_sidecar_sha256':expected_digests[1],
            'PDB_map_read_only_input':str(pdb_map),'PDB_map_access':'GenFv WriteMapFile fopen r only',
            'expected_FD_sha256':m['saved_compact_FD']['sha256']}
    print(json.dumps({'started':True,'host_linux_pid':os.getpid(),'private_directory':str(private)}),flush=True)
    try:
        for p in sec_files:shutil.copy2(p,private/'inputs'/p.name)
        shutil.copy2(container,private/'inputs/container.ffs')
        config=Path(m['compact_config']['config']['path']).read_text()
        expected_paths=iter([private/'inputs'/(guid+'.ffs'),private/'inputs/container.ffs'])
        config=re.sub(r'^EFI_FILE_NAME\s*=.*$',lambda _: 'EFI_FILE_NAME = '+str(next(expected_paths)),config,flags=re.M)
        assert next(expected_paths,None) is None
        (private/'FVMAIN_COMPACT.inf').write_text(config)
        argv=[tool['path'],'-g',m['compact_FV']['filesystem_guid'],'-i',str(private/'FVMAIN_COMPACT.inf'),'-o',str(private/'compact.fd')]
        result['argv']=argv;write(private/'result.json',result)
        with (private/'stdout.log').open('wb') as out,(private/'stderr.log').open('wb') as err:
            done=subprocess.run(argv,cwd=private,stdout=out,stderr=err,timeout=120)
        result['tool_returncode']=done.returncode;assert done.returncode==0
        actual=(private/'compact.fd').read_bytes()
        result['actual_FD_sha256']=sha(actual);result['actual_FD_bytes']=len(actual)
        result['SEC_full_FFS_byte_equal']=actual[sec['offset']:sec['offset']+sec['bytes']]==expected[sec['offset']:sec['offset']+sec['bytes']]
        result['SEC_full_FFS_sha256']=sha(actual[sec['offset']:sec['offset']+sec['bytes']])
        result['FV_vector_hex']=actual[:16].hex();result['FV_checksum_hex']=actual[50:52].hex()
        result['full_FD_byte_equal']=actual==expected
        assert result['SEC_full_FFS_byte_equal'] and result['full_FD_byte_equal'],'any SEC/FD byte difference is failure'
        result['passed']=True
    except BaseException as exc:result['error']=repr(exc);result['traceback']=traceback.format_exc()
    finally:
        result['inputs_after']=snap();result['parent_inputs_unchanged']=before==result['inputs_after']
        result['parent_mountinfo_unchanged']=mount_before==Path('/proc/self/mountinfo').read_bytes()
        result['passed'] &= result['parent_inputs_unchanged'] and result['parent_mountinfo_unchanged']
        result['evidence']={p.name:sha(p.read_bytes()) for p in private.iterdir() if p.is_file() and p.name!='result.json'}
        write(private/'result.json',result)
        public={k:v for k,v in result.items() if k not in ['inputs_before','inputs_after','traceback']}
        public['parent_input_count']=len(before);public['private_result_sha256']=sha((private/'result.json').read_bytes())
        public['executed_runner_sha256']=sha(Path(__file__).read_bytes())
        write(own/'result.json',public);print(json.dumps(public,indent=2))
    return 0 if result['passed'] else 1
if __name__=='__main__':
    if sys.argv[1:]==['--execute-compact-baseline']:raise SystemExit(run())
    elif sys.argv[1:] in [[],['--check-local']]:print(json.dumps({'checked':True,'execution':False,'private_exists':private.exists(),'sidecar_PE_reloc':[55360,64],'PDB_read_only_map':str(pdb_map)}))
    else:raise SystemExit('use --check-local or separately authorized --execute-compact-baseline')
