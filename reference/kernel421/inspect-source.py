"""Read the actual deployed source's frame/IPA contracts before changing them."""
from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('storage420',HERE.parent/'kernel420/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
tree=storage.candidate()/'src/libcamera-v0.7.2'
for folder in ['src/ipa/camss-vfe','include/libcamera/ipa','src/libcamera/pipeline/camss-vfe']:
 print(folder,':',[p.name for p in (tree/folder).iterdir() if p.is_file()])
for name in ['src/ipa/camss-vfe/camss.cpp','src/libcamera/pipeline/camss-vfe/camss_vfe.cpp']:
 lines=(tree/name).read_text().splitlines();print('\nFUNCTIONS',name)
 for i,l in enumerate(lines):
  if any(n in l for n in ['processStats','queueRequest','fillParams','paramsReady','metadataReady','imageProcessed','imageReady','statsReady','struct Frame','struct Pending','private:','processRequest','prepareIpe','releaseRequest','completeRequest','processContext']):
   print(i+1,l)
for p in (tree/'include/libcamera/ipa').glob('*camss*'):
 print('\nINTERFACE',p.name);print(p.read_text())
for p in (tree/'src/ipa/camss-vfe').glob('*.h'):
 print('\nHEADER',p.name);print(p.read_text()[:14000])
