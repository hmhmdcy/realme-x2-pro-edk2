"""Small read-only symbol-set supplement. No mounts/build/old module fallback."""
from pathlib import Path
import hashlib,json,struct,sys,tarfile
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
PRIVATE=Path('/mnt/e/edk2-samurai-out')
OUT=Path('/home/cy122/charging-management-20261023/gauge-image501-B-repro-01')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def symbols_raw(raw):
    h=struct.unpack_from('<16sHHIQQQIHHHHHH',raw)
    assert h[0][:6]==b'\x7fELF\x02\x01' and h[2]==183
    sections=[struct.unpack_from('<IIQQQQIIQQ',raw,h[6]+i*h[11]) for i in range(h[12])]
    imports=set();exports=set();weak=set()
    for s in sections:
        if s[1]!=2:continue
        table=sections[s[6]];strings=raw[table[4]:table[4]+table[5]]
        for off in range(s[4],s[4]+s[5],s[9]):
            n,info,other,index,value,size=struct.unpack_from('<IBBHQQ',raw,off)
            name=strings[n:].split(b'\0',1)[0].decode()
            if not name:continue
            if index==0 and info>>4==1:imports.add(name)
            if index==0 and info>>4==2:weak.add(name)
            if index!=0 and name.startswith('__ksymtab_') and name!='__ksymtab_strings':
                exports.add(name.removeprefix('__ksymtab_'))
    return imports,exports,weak
def symbols(p):return symbols_raw(p.read_bytes())
wrapper=PRIVATE/'kernel481/formal-expected-private.json'
assert sha(wrapper)=='1c4584915dade64a0978a0138c6775bf99e56af9f8036d7d2276c33f132f4705'
formal=json.loads(wrapper.read_bytes())['expected']
paths={}
for name,r in formal['modules'].items():
    found=list((PRIVATE/'kernel441').glob(Path(r['path']).stem+'-intree-r4.ko'))
    assert len(found)==1 and sha(found[0])==r['sha256'];paths[name]=found[0]
sensor=PRIVATE/'kernel468/s5k3m5-mode2-build2.ko'
sensor_sha=next(v for k,v in formal['installed_files'].items() if k.endswith('/s5k3m5.ko'))
assert sha(sensor)==sensor_sha;paths['s5k3m5']=sensor
dep_receipt=REF/'kernel441/intree-build-validation.json'
for r in json.loads(dep_receipt.read_bytes())['modules']:
    if not r['runtime_candidate']:
        p=Path(r['private_path']);assert sha(p)==r['sha256'];paths['dependency:'+r['name']]=p
assert len(paths)==11
builtin_path=OUT/'builtin-exports-candidate.json'
builtin=json.loads(builtin_path.read_bytes())
assert len(builtin)==15097 and all(r[2]=='vmlinux' for r in builtin.values())
parts={name:symbols(p) for name,p in paths.items()}
current_only_exports=set().union(*(r[1] for r in parts.values()))
# The only missing provider in this reduced 11-file set is the retained CCI.
# Bind its bytes to the original complete module archive/inventory, without a mount.
inventory_path=PRIVATE/'kernel363/installed-module-inventory-private.json'
inventory=json.loads(inventory_path.read_bytes())
frozen_abi=json.loads((HERE.parent/'gauge-image501-repro-candidate/abi-result.json').read_bytes())
assert sha(inventory_path)==frozen_abi['original_module_inventory_sha256']
cci_name='kernel/drivers/media/v4l2-core/v4l2-cci.ko'
cci_sha='232c5140e5bb7f8058bcb103822a9c643e12b5fe60acf8fe2fd17dc58234e705'
assert inventory[cci_name]==cci_sha
archive=PRIVATE/'kernel363/modules-k363-private.tar.gz'
assert sha(archive)=='fca01dab22b0a3917f9ce5600059d00b29aa9685381c2cd2f2e4867b9fb8f73b'
archive_entry='usr/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/'+cci_name
with tarfile.open(archive,'r:gz') as t:
    item=t.getmember(archive_entry);assert item.isfile()
    cci_raw=t.extractfile(item).read()
assert hashlib.sha256(cci_raw).hexdigest()==cci_sha
assert all(Path(r['path']).name!='v4l2-cci.ko' for r in formal['modules'].values())
assert not any(n.endswith('/v4l2-cci.ko') for n in formal['installed_files'])
providers_all={**parts,'retained:v4l2-cci':symbols_raw(cci_raw)}
current_exports=set().union(*(r[1] for r in providers_all.values()))
rows={}
for name,p in paths.items():
    strong,exports,weak=parts[name]
    nonbuiltin=strong-set(builtin)
    providers={symbol:sorted(n for n,r in providers_all.items() if symbol in r[1]) for symbol in sorted(nonbuiltin)}
    rows[name]={'sha256':sha(p),'strong_import_count':len(strong),'weak_import_count':len(weak),
                'strong_nonbuiltin_imports':sorted(nonbuiltin),'current_provider_map':providers,
                'needs_retained_cci':sorted(nonbuiltin-current_only_exports),
                'unresolved_without_all_old_names':sorted(strong-set(builtin)-current_exports)}
cci_imports,cci_exports,cci_weak=providers_all['retained:v4l2-cci']
cci_unresolved=sorted(cci_imports-set(builtin)-current_only_exports)
result={'passed':all(not r['unresolved_without_all_old_names'] for r in rows.values()) and not cci_unresolved,
        'scope':'actual 11 cached current ELF files plus exact candidate builtin rows and one exact retained CCI; no all_old_names fallback',
        'module_count':len(paths),'builtin_export_count':len(builtin),'current_export_union_count':len(current_exports),
        'original_778_export_union_used':False,'rows':rows,
        'retained_cci':{'sha256':cci_sha,'archive_sha256':sha(archive),'archive_entry':archive_entry,
                       'not_in_481_explicit_replacements':True,'exports':sorted(cci_exports),
                       'strong_imports':sorted(cci_imports),'weak_imports':sorted(cci_weak),
                       'unresolved_without_old_union':cci_unresolved},
        'inputs':{'formal481_sha256':sha(wrapper),'builtin_rows_sha256':sha(builtin_path),
                  'dependency_receipt_sha256':sha(dep_receipt)},
        'source_sha256':sha(Path(__file__)),'mount_called':False,'build_called':False,'device_access':False}
(HERE/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':result['passed'],'module_count':len(paths),
                  'nonbuiltin_import_counts':{n:len(r['strong_nonbuiltin_imports']) for n,r in rows.items()},
                  'missing_without_old_exports':{n:r['unresolved_without_all_old_names'] for n,r in rows.items()}},indent=2),flush=True)
raise SystemExit(0 if result['passed'] else 1)
