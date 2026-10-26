from pathlib import Path
import importlib.util,shutil,subprocess
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354'
assert subprocess.check_output(['git','-C',str(source),'branch','--show-current'],text=True).strip()=='samurai-icp-a5-bootstrap356'
for path in (HERE/'kernel').glob('*'):
 if path.suffix in ['.c','.h']:shutil.copyfile(path,source/'drivers/media/platform/qcom/camss'/path.name)
print('Updated only the current ICP candidate source files.')
