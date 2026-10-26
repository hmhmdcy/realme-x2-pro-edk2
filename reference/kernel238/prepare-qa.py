from pathlib import Path
import ast
R=Path(__file__).resolve().parent
mapping={'inspect-r13-full-features.py':'inspect-full-features.py','collect-r13-forward-packages.py':'collect-forward-packages.py','host-r13-runtime-qa.py':'host-runtime-qa.py'}
for old,new in mapping.items():
 text=(R.parent/'kernel225'/old).read_text().replace('kernel225','kernel238').replace('stage=225','stage=238').replace('225-r13','238-r14').replace('225-r13','238-r14').replace('r13','r14').replace('0.1.0-r8','0.1.0-r9').replace('r14-package-build-validation.json','package-build-validation.json')
 ast.parse(text);p=R/new;assert not p.exists();p.write_text(text)
print('Prepared full feature, APK and IPA runtime QA for r14/r9')
