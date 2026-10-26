"""Build full-feature signed r21/r16 with normal abuild from retained r20 cache."""
from pathlib import Path
R=Path(__file__).resolve().parent
text=(R.parent/'kernel239/build-r15.py').read_text()
changes=[("kernel239')","kernel273')"),('libcamera214-before239-r15','libcamera214-before273-r21'),
 ('libcamera239-r15-built','libcamera273-r21-built'),('libcamera238-r14-built','libcamera271-r20-built'),
 ('libcamera239-r15','libcamera273-r21'),('samurai-camera-config239-r15','samurai-camera-config273-r21'),
 ('packages239-r15','packages273-r21'),('packages-config239-r15','packages-config273-r21'),
 ('r15-source-validation.json','package-source-validation.json'),("proof['patch_count']==22","proof['patch_count']==25"),
 ('0022-soft-initial-parameters.patch','0025-s5kgw1-native-gain-helper.patch'),
 ('stage=239','stage=273'),('r15-build-state','r21-build-state'),
 ('r15-patch-apply','r21-patch-apply'),('full-r15-build','full-r21-build'),
 ('r15-package-build-validation','r21-package-build-validation'),('prior21','prior24'),
 ('r14-cache-before','r20-cache-before'),('r14_cache_files','r20_cache_files'),('retained-r14','retained-r20'),
 ('config-r10-build','config-r16-build')]
for a,b in changes:
 assert a in text,a;text=text.replace(a,b)
old="process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT);record(phase='full-feature-r15-build-live',pid=process.pid,source_inputs_verified=checked);ret=process.wait()"
new="process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT);record(phase='full-feature-r21-build-live',pid=process.pid,start_ticks=Path('/proc',str(process.pid),'stat').read_text().rsplit(')',1)[1].split()[19],source_inputs_verified=checked);ret=process.wait()"
assert old in text;text=text.replace(old,new)
assert "cache=SDK/'work/libcamera271-r20-built'" in text
exec(compile(text,'build-packages273-generated.py','exec'),dict(__file__=str(R/'build-packages-generated.py')))
