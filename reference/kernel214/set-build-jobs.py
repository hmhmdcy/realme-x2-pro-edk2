from pathlib import Path
import hashlib,json,shutil
here=Path(__file__).resolve().parent;repo=here.parents[1];port=repo/'linux-port/packages/libcamera';recipe=port/'APKBUILD'
before=recipe.read_text();assert before.count('\tmeson compile -C output\n')==1;recipe.write_text(before.replace('\tmeson compile -C output\n','\tmeson compile -C output -j "${JOBS:-4}"\n'))
for path in [port/'source-lock.json',here/'full-port-source-validation.json']:
    report=json.loads(path.read_text());report['source_files_sha256']['APKBUILD']=hashlib.sha256(recipe.read_bytes()).hexdigest();report['explicit_build_jobs_parameter']=True;path.write_text(json.dumps(report,indent=2)+'\n')
shutil.copyfile(recipe,Path('/home/cy122/x2pro-linux/libcamera214-root/work/libcamera/APKBUILD'))
print('Full recipe compile parallelism now explicitly follows JOBS; root staging and source locks updated.')
