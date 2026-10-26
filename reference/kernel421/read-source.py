from pathlib import Path
import importlib.util,sys
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('storage420',HERE.parent/'kernel420/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
tree=storage.candidate()/'src/libcamera-v0.7.2'
for arg in sys.argv[1:]:
 name,a,b=arg.rsplit(':',2);lines=(tree/name).read_text().splitlines();print('\nFILE',name)
 for i in range(int(a)-1,min(int(b),len(lines))):print(f'{i+1}: {lines[i]}')
