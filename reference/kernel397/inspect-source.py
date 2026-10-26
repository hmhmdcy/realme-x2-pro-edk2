"""Read current transfer ownership and adapter interfaces before changing them."""
from pathlib import Path
import importlib.util,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()=='46fdb7c96b04825dc1802f8280685a4c4e709615'
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).strip()
base=source/'drivers/media/platform/qcom/camss'
for name in ['camss-icp-a5-boot.c','camss-icp-a5-boot.h','camss-icp-a5-ipe.c','camss-icp-a5-ipe.h','camss-icp-a5-m2m.c','camss-icp-a5-memory.c']:
 (P/(name+'.before')).write_bytes((base/name).read_bytes())
s=(base/'camss-icp-a5-boot.c').read_text();a=s.index('int camss_a5_ipe_run_status(');b=s.index('EXPORT_SYMBOL_GPL(camss_a5_ipe_run_status)',a);print(s[a:b])
m=(base/'camss-icp-a5-m2m.c').read_text();print('\n'.join(l for l in m.splitlines() if any(x in l for x in ['ctrl', 'request', 'run_status', 'm2m_ctx', 'struct camss'])))
