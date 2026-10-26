from pathlib import Path
import ast,hashlib,json,subprocess,tarfile
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel154')
out=Path('/mnt/e/edk2-samurai-out/kernel154')
build=json.loads((ref/'build-package-validation.json').read_text())
assert build['dtb_sha256']==json.loads((ref.parent/'kernel153/build-package-validation.json').read_text())['dtb_sha256']
build['dtb_unchanged']=True
(out/'build-package-validation.json').write_text(json.dumps(build,indent=2)+'\n')
files=['collect-preflash.py','quiesce-current153.sh','check-quiesce.py','freeze-for-bootloader.sh',
    'capture-startup.py','k154-startup-trace','display-power.py','capture-display-cycles.py','verify-runtime.py']
for name in files:
    text=(ref/name).read_text()
    if name.endswith('.py'):ast.parse(text)
    if name.endswith('.sh') or name=='k154-startup-trace':subprocess.run(['sh','-n',str(ref/name)],check=True)
with tarfile.open(out/'deployment-tools-private.tar','w') as tar:
    for name in files:tar.add(ref/name,arcname=name)
    tar.add(out/'build-package-validation.json',arcname='build-package-validation.json')
report=dict(stage=154,tools=len(files)+1,metadata_dependency_included=True,
    archive_sha256=hashlib.sha256((out/'deployment-tools-private.tar').read_bytes()).hexdigest(),
    source_kernel_guard=153,target_kernel=154,current_card_guard=1)
(ref/'deployment-tools-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
