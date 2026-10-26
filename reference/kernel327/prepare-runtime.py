"""Reuse the installed-IPA capture tool; no module or package rebuild/install."""
from pathlib import Path
import json, tarfile
import host

HERE = Path(__file__).resolve().parent
P = host.PRIVATE
s = (HERE.parent / 'kernel324/native-probe.py').read_text()
s = s.replace("models=sys.argv[2].split(',') if len(sys.argv)>2 else ['imx319']",
              "models=list(json.loads((root/'cases.json').read_text()))")
s = s.replace("item['output'],item['sensor_size']]", "item['output'],item['sensor_size'],str(item['test_pattern'])]")
s = s.replace('stage=324', 'stage=327')
(HERE / 'native-probe.py').write_text(s)
with tarfile.open(P / 'runtime.tar.gz', 'w:gz') as tar:
    tar.add(HERE / 'native-probe.py', arcname='worker.py')
    tar.add(HERE / 'cases.json', arcname='cases.json')
    tar.add(P / 'profiles', arcname='profiles')
    tar.add(P.parent / 'kernel313/pipeline-fixture', arcname='pipeline-fixture')
    tar.add('/home/cy122/x2pro-linux/libcamera214-root/private/camss325-runtime/lsc-smoke', arcname='bin/lsc-smoke')
print('Prepared temporary paired unit/factory profiles with unchanged capture binaries.')
