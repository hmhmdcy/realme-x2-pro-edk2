"""Adapt the checked FAT16 Image-only constructor to the actual505 artifact."""
from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
source=(REF/'charging-oem-audit-20261023/image504-budget-logdump-candidate/package-logdump.py').read_text()
def replace(before,after):
 global source
 assert source.count(before)==1,(before[:80],source.count(before));source=source.replace(before,after)
replace("OLD=ROOT/'charging-management-20261023/gauge-image502-logdump-private-01/logdump-gauge502-private.img'","OLD=ROOT/'charging-management-20261023/image504-budget-logdump-private-01/logdump-image504-private.img'")
replace("IMAGE=Path('/home/cy122/charging-management-20261023/dwc-image504-budget-fence-01/build/arch/arm64/boot/Image')","IMAGE=Path('/home/cy122/charging-management-20261023/apsd-image505-01/build-upper/arch/arm64/boot/Image')")
replace("OUT=ROOT/'charging-management-20261023/image504-budget-logdump-private-01'","OUT=ROOT/'charging-management-20261023/apsd-image505-logdump-private-01'")
start=source.index('def load_504_proof():');end=source.index('\ndef execute():',start)
source=source[:start]+'''def check_local():
    build=json.loads(read_bytes(HERE/'kernel-build-r2-result.json'));assert build['passed']
    assert build['shared_and_baseline_before']==build['shared_and_baseline_after']
    assert build['build']['original_gauge_object_and_initramfs_exact']
    old=pinned(OLD,'4453d46202f4446810c8f72524a034a28acf3695f59eb12dbde8cf530e356d83')
    f=parse_fat(old)
    assert f['files']['Image']['sha256']=='f6477d01d029cec888cafa739db0336e570274e9a3c38d4d5233959dd218a3f4'
    assert f['files']['SAMURAI.DTB']['sha256']=='a82383fa30609bb5e1400f8af12055abdbca7373734c983549d9f437afae2cc5'
    for path,digest in TOOLS.values():pinned(Path(path),digest)
    row=build['build']['Image505'];image=pinned(IMAGE,row['sha256']);assert len(image)==row['bytes']
    assert row['sha256']=='b91a5a667d55c34d9f8fc5aa515161c7e824b20b167be2415a982e96fa949d43'
    return old,image,f
'''+source[end:]
start=source.index('    paths=[OLD,IMAGE,Path(__file__)');end=source.index('    before=',start)
source=source[:start]+"    paths=[OLD,IMAGE,Path(__file__),HERE/'kernel-build-r2-result.json',HERE/'assembly-inputs.json']\n    paths += [Path(p) for p,_ in TOOLS.values()]\n"+source[end:]
source=source.replace('Image504','Image505').replace('logdump-image504-private.img','logdump-apsd505-private.img')
# Preserve the actual current4443 carrier source, not a newly named file.
source=source.replace("image504-budget-logdump-private-01/logdump-apsd505-private.img","image504-budget-logdump-private-01/logdump-image504-private.img")
source=source.replace("save(HERE/'logdump-result.json'","save(HERE/'logdump-package-result.json'")
source=source.replace('private undeployed saved-candidate502 FAT Image505 replacement only','private Image505 replacement in actual current4453 FAT; no device access')
ast.parse(source)
with (HERE/'package-logdump.py').open('x') as stream:stream.write(source)
print(dict(prepared=True))
