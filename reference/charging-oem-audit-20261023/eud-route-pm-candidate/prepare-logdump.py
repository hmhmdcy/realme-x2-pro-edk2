"""Reuse505's FAT-only constructor; no firmware or boot partition rebuild."""
from pathlib import Path
import ast,hashlib,json
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'apsd-image505-integration-candidate'
source=(OLD/'package-logdump.py').read_text();origin=hashlib.sha256(source.encode()).hexdigest()
tree=ast.parse(source);node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='check_local')
before=ast.get_source_segment(source,node)
after='''def check_local():
    build=json.loads(read_bytes(HERE/'image-build-r2-result.json'));assert build['passed']
    assert build['parent_inputs_unchanged'] and build['parent_mounts_unchanged']
    assert build['build']['builtin_exports_exact'] and build['build']['gauge_initramfs_and_builtin_metadata_exact']
    for target,digest in build['build']['changed_sources'].items():
        path=HERE/('samurai-apsd-owner.c' if target.endswith('samurai-apsd-owner.c') else 'samurai-eud-route.h' if target.endswith('.h') else 'samurai-eud-route.c')
        assert sha(path.read_bytes())==digest
    old=pinned(OLD,'b38826d76d761ca03da3bad997b3651ab530e5aa4652d0825eb5e29f228160c4');f=parse_fat(old)
    assert f['files']['Image']['sha256']=='b91a5a667d55c34d9f8fc5aa515161c7e824b20b167be2415a982e96fa949d43'
    assert f['files']['SAMURAI.DTB']['sha256']=='a82383fa30609bb5e1400f8af12055abdbca7373734c983549d9f437afae2cc5'
    for path,digest in TOOLS.values():pinned(Path(path),digest)
    row=build['build']['Image506'];image=pinned(IMAGE,row['sha256']);assert len(image)==row['bytes']
    return old,image,f'''
assert source.count(before)==1;source=source.replace(before,after)
source=source.replace("OLD=ROOT/'charging-management-20261023/image504-budget-logdump-private-01/logdump-image504-private.img'","OLD=ROOT/'charging-management-20261023/apsd-image505-logdump-private-01/logdump-apsd505-private.img'")
source=source.replace("IMAGE=Path('/home/cy122/charging-management-20261023/apsd-image505-01/build-upper/arch/arm64/boot/Image')","IMAGE=Path('/home/cy122/charging-management-20261023/route-pm-image506-02/build-upper/arch/arm64/boot/Image')")
source=source.replace("OUT=ROOT/'charging-management-20261023/apsd-image505-logdump-private-01'","OUT=ROOT/'charging-management-20261023/route-pm-image506-logdump-private-01'")
source=source.replace("paths=[OLD,IMAGE,Path(__file__),HERE/'kernel-build-r2-result.json',HERE/'assembly-inputs.json']","paths=[OLD,IMAGE,Path(__file__),HERE/'image-build-r2-result.json']")
source=source.replace("target=OUT/'logdump-apsd505-private.img'","target=OUT/'logdump-route506-private.img'")
source=source.replace('Image505','Image506').replace('actual current4453 FAT','actual current b388 FAT')
ast.parse(source)
with (HERE/'package-logdump.py').open('x') as stream:stream.write(source)
(HERE/'logdump-derivation.json').write_text(json.dumps(dict(prepared=True,constructor_origin_sha256=origin,Image_only_change=True,phone_accessed=False),indent=2)+'\n')
print(json.dumps(dict(prepared=True)))
