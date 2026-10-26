"""Full-feature r20/r15 native abuild from retained r19 source and objects."""
from pathlib import Path

R=Path(__file__).resolve().parent
text=(R.parent/'kernel239/build-r15.py').read_text()
for a,b in [
    ("kernel239')", "kernel271')"),
    ('libcamera214-before239-r15','libcamera214-before271-r20'),
    ('libcamera239-r15-built','libcamera271-r20-built'),
    ('libcamera238-r14-built','libcamera268-r19-built'),
    ('libcamera239-r15','libcamera271-r20'),
    ('samurai-camera-config239-r15','samurai-camera-config271-r20'),
    ('packages239-r15','packages271-r20'),('packages-config239-r15','packages-config271-r20'),
    ('r15-source-validation.json','gain-source-validation.json'),
    ("proof['patch_count']==22", "proof['patch_count']==24"),
    ('0022-soft-initial-parameters.patch','0024-s5k3m5-native-gain-helper.patch'),
    ('stage=239','stage=271'),('before239','before271'),
    ('r15-build-state','r20-build-state'),('r15-patch-apply','r20-patch-apply'),
    ('full-r15-build','full-r20-build'),('r15-package-build-validation','r20-package-build-validation'),
    ('prior21','prior23'),('stage239','stage271')
]:text=text.replace(a,b)
assert "cache=SDK/'work/libcamera268-r19-built'" in text
exec(compile(text,'build-gain-packages-generated.py','exec'),dict(__file__=str(R/'build-gain-packages-generated.py')))
