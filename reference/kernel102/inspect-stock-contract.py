from pathlib import Path, PurePosixPath
import gzip, hashlib, json, re, struct, tarfile
root=Path('/mnt/e/RealmeX2Pro edk2')
out=Path('/mnt/e/edk2-samurai-out/kernel102')
sha=lambda b:hashlib.sha256(b).hexdigest()
files={}
with tarfile.open(out/'stock-audio-contract.tar') as tar:
    for m in tar:
        if not m.isfile():continue
        parts=PurePosixPath(m.name).parts
        assert parts[0]=='k102-stock-audio-contract' and '..' not in parts
        name=str(PurePosixPath(*parts[1:]));assert name not in files
        files[name]=tar.extractfile(m).read()
checked=set()
for line in files['SHA256SUMS'].decode().splitlines():
    digest,name=line.split('  ',1);name=name.removeprefix('./')
    assert name not in checked and sha(files[name])==digest
    checked.add(name)
assert checked==files.keys()-{'SHA256SUMS'}
data=gzip.decompress(files['stock-dtbo.img.gz'])
assert len(data)==49152*512
assert sha(data)==files['dtbo-before.sha'].decode().split()[0]
assert all(line.split()[0]==sha(data) for line in files['dtbo-after.sha'].decode().splitlines())
assert '/tmp/k102-stock-audio-contract/mount-vendor' not in files['mounts-after.txt'].decode()
assert 'ro,nosuid,nodev,noexec' in files['mounts-during.txt'].decode() and 'norecovery' in files['mounts-during.txt'].decode()
assert len(files['nv-check.txt'].splitlines())==6 and all(line.endswith(b': OK') for line in files['nv-check.txt'].splitlines())
assert files['persist.sha'].decode().split()[0]==(out.parent/'kernel101/persist-before.sha').read_text().split()[0]
dest=out/'stock-audio-extracted'
assert not dest.exists();dest.mkdir()
for name,b in files.items():
    if name.startswith('vendor/'):
        p=dest/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
(dest/'dtbo.img').write_bytes(data)
magic,total,hs,es,n,off,page,ver=struct.unpack_from('>8I',data)
assert magic==0xd7b7ab1e and hs==32 and es>=32 and off>=32
assert total<=len(data) and n>0 and off+n*es<=total
ns={}
exec((root/'reference/kernel93/verify-firmware.py').read_text().split('\ndt_audit=')[0],ns)
summary=[]
nodes_json={}
for i in range(n):
    size,start,ident,rev,*custom=struct.unpack_from('>8I',data,off+i*es)
    assert start+size<=total
    blob=data[start:start+size]
    assert blob[:4]==bytes.fromhex('d00dfeed')
    nodes=ns['fdt_nodes'](blob)
    (dest/f'overlay-{i}.dtbo').write_bytes(blob)
    nodes_json[str(i)]={p:{key:value.hex() for key,value in props.items()} for p,props in nodes.items()}
    components=[]
    for p,props in nodes.items():
        comp=props.get('compatible',b'').decode(errors='replace').strip('\0').replace('\0',',')
        if re.search('wcd|slim|989|tavil|tfa|speaker|audio',p+' '+comp,re.I):
            components.append(dict(path=p,compatible=comp,properties=sorted(props)))
    summary.append(dict(index=i,bytes=size,ident=ident,revision=rev,custom=custom,components=components))
(out/'stock-overlay-nodes-private.json').write_text(json.dumps(nodes_json,indent=2)+'\n')
report=dict(stock_contract_archive_audit_pass=True,private_files=len(checked),archive_sha256=sha((out/'stock-audio-contract.tar').read_bytes()),
  dtbo_readonly_hash_matches=True,dtbo_bytes=len(data),dtbo_total_bytes=total,dtbo_entries=n,dtbo_version=ver,
  nv_unchanged=True,persist_unchanged=True,vendor_unmounted=True,overlays=summary)
(out/'stock-contract-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
