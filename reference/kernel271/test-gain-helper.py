"""Exercise the actual built helper factory and reject the old r19 implementation."""
from pathlib import Path
import hashlib, json, shutil, subprocess
import host
R=Path(__file__).resolve().parent
text=(R.parent/'kernel238/test-gain-helper.py').read_text()
for a,b in [("kernel238')","kernel271')"),('package-build-validation.json','r20-package-build-validation.json'),
 ('gain-helper-test238','gain-helper-test271'),("[('r14','libcamera238-r14-built'),('negative-r13','libcamera225-r13-built')]","[('r20','libcamera271-r20-built'),('negative-r19','libcamera268-r19-built')]"),
 ("label=='r14'","label=='r20'"),('stage=238','stage=271'),('negative_r13_missing_helper_verified','negative_r19_missing_helper_verified')]:text=text.replace(a,b)
assert "('r20','libcamera271-r20-built')" in text
exec(compile(text,'gain-helper-test-generated.py','exec'),dict(__file__=str(R/'gain-helper-test-generated.py')))
