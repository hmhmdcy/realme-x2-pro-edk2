"""Inspect the actual maintained request and geometry implementation."""
from pathlib import Path
import importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage);source=storage.mounted_build().parent/'source354';state=json.loads((HERE.parent/'kernel404/source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit'] and not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
for name in ['camss-icp-a5-ipe.c','camss-icp-a5-ipe.h','camss-icp-a5-boot.c','camss-icp-a5-boot.h']:(P/(name+'.before')).write_bytes((source/'drivers/media/platform/qcom/camss'/name).read_bytes())
state.update(stage=405,source_unchanged_from404=True);(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(dict(source_clean=True,parent=state['commit'],phone_accessed=False)))
