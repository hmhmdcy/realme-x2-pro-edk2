"""Refresh the retained package source and cumulative patch after a pipeline edit."""
from pathlib import Path
import difflib,hashlib,json,shutil

HERE=Path(__file__).resolve().parent
SDK=Path('/home/cy122/x2pro-linux/libcamera214-root')
BASE=SDK/'work/libcamera278-r24-r3-built/src/libcamera-v0.7.2'
SOURCE=SDK/'work/libcamera316-r25-built/src/libcamera-v0.7.2'
relative='src/libcamera/pipeline/camss-vfe/camss_vfe.cpp'
new=(HERE/'pipeline/camss_vfe.cpp').read_text()
(SOURCE/relative).write_text(new)
patch=HERE/'0029-camss-hardware-pipeline.patch'
text=patch.read_text()
header='a/'+relative if (BASE/relative).exists() else '/dev/null'
start=text.index('--- '+header+'\n+++ b/'+relative+'\n')
end=text.find('\n--- ',start+1)
if end==-1:end=len(text)
else:end+=1
replacement=''.join(difflib.unified_diff(
    (BASE/relative).read_text().splitlines(True) if (BASE/relative).exists() else [],
    new.splitlines(True),fromfile=header,tofile='b/'+relative))
assert replacement
patch.write_text(text[:start]+replacement+text[end:])
for recipe in [HERE/'recipes/libcamera',SDK/'work/libcamera316-r25']:
    shutil.copyfile(patch,recipe/patch.name)
    apkbuild=recipe/'APKBUILD';lines=apkbuild.read_text().splitlines(True)
    indices=[i for i,line in enumerate(lines) if line.endswith('  '+patch.name+'\n')]
    assert len(indices)==1
    lines[indices[0]]=hashlib.sha512(patch.read_bytes()).hexdigest()+'  '+patch.name+'\n'
    apkbuild.write_text(''.join(lines))
report_path=HERE/'package-source-validation.json'
report=json.loads(report_path.read_text())
report['changed_source_sha256'][relative]=hashlib.sha256(new.encode()).hexdigest()
report_path.write_text(json.dumps(report,indent=2)+'\n')
print('Updated retained pipeline and cumulative recipe patch.')
