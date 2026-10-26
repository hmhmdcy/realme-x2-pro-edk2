from pathlib import Path
import hashlib,json
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
out=Path('/mnt/e/edk2-samurai-out/kernel113')
reports={name:json.loads((ref/(name+'-reference-validation.json')).read_text()) for name in ('c28','c35')}
first=reports['c28']['files'];second=reports['c35']['files']
assert first.keys()==second.keys()
differences={}
for name in first:
    a=(out/'c28-reference-private/firmware'/name).read_bytes()
    b=(out/'c35-reference-private/firmware'/name).read_bytes()
    assert hashlib.sha256(a).hexdigest()==first[name]
    assert hashlib.sha256(b).hexdigest()==second[name]
    if a!=b:
        differences[name]=dict(c28_bytes=len(a),c35_bytes=len(b),same_size=len(a)==len(b),
                              differing_byte_count=sum(x!=y for x,y in zip(a,b))+abs(len(a)-len(b)))
report=dict(c28_c35_slpi_files_identical=not differences,file_count=len(first),
            different_files= differences,same_firmware_version='SLPI.HY.2.2-00098',
            c35_linux_trial_run=False,source_packages_crc_verified=True,
            same_version_string_does_not_prove_identical_image=True)
(ref/'c35-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
