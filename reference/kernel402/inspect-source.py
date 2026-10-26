"""Read the maintained request allocation and pinned Gamma source privately."""
from pathlib import Path
import importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';base=source/'drivers/media/platform/qcom/camss'
for name in ['camss-icp-a5-boot.c','camss-icp-a5-ipe.c','camss-icp-a5-colour.c']:(P/name).write_bytes((base/name).read_bytes())
repo=Path('/home/cy122/x2pro-linux/refs/CamxChi-k117');rev='9f17f1b568626b393e785b369c5dc94543774d7a'
for rel in ['camx/src/hwl/isphwsetting/titan17x/camxipegamma15titan17x.cpp','camx/src/hwl/isphwsetting/titan17x/camxipegamma15titan17x.h','camx/src/csl/camxcdmdefs.h','chi-cdk/api/isp/chiipedefs.h']:
 (P/Path(rel).name).write_bytes(subprocess.check_output(['git','-C',str(repo),'show',rev+':'+rel]))
print('Saved bounded current allocation and pinned Gamma source privately.')
