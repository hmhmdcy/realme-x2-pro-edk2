from pathlib import Path
import importlib.util,json,shutil,subprocess
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage);storage.mounted_build()
state=json.loads((HERE/'source-state.json').read_text());tree=Path(state['source'])
for relative in state['changed_sources']:shutil.copyfile(tree/relative,HERE/'kernel'/Path(relative).name)
(HERE/'ife-gamma-driver.patch').write_bytes(subprocess.check_output(['git','-C',str(tree),'diff',state['base_commit']]))
q=subprocess.run(['perl',str(tree/'scripts/checkpatch.pl'),'--no-tree',str(HERE/'ife-gamma-driver.patch')],capture_output=True,text=True)
Path('/mnt/e/edk2-samurai-out/kernel348/checkpatch-final.log').write_text(q.stdout+q.stderr);print(q.stdout+q.stderr)
assert '0 errors, 0 warnings' in q.stdout
