"""Keep the already measured302 conversion candidate before public mode completion."""
from pathlib import Path
import hashlib,json,tarfile
import host
HERE=Path(__file__).resolve().parent;tree=Path('/home/cy122/x2pro-linux/libcamera214-root/work/libcamera299-inline')
build=json.loads((HERE/'build-validation.json').read_text());assert build['attempt']==2 and build['build_exit']==0
for name,digest in build['source_sha256'].items():assert hashlib.sha256((tree/name).read_bytes()).hexdigest()==digest
archive=host.PRIVATE/'pre-manual-modes302-source-private.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for name in build['source_sha256']:tar.add(tree/name,arcname='sdk/'+name,recursive=False)
 for name in ['pipeline-smoke.cpp','ipa-contract.cpp','build-validation.json','ipa-contract-validation.json','ipa-bundle-r1-validation.json','native-controls.py']:
  tar.add(HERE/name,arcname='reference302/'+name,recursive=False)
print('Preserved measured302 sources before completing standard manual mode controls.')
