from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel449/check-inputs.py').read_text()
source=source.replace("HERE.parent/'kernel448/source-state.json'","HERE/'source-state.json'").replace("HERE.parent/'kernel448/build-validation.json'","HERE/'build-validation.json'")
source=source.replace("P.parent/'kernel448'/row['name']","P/row['name']")
source=source.replace("for proof in ['source','capacity','unprivileged','reentry']:","for proof in ['source','reentry','retirement']:").replace("HERE.parent/'kernel448'/(proof+'-validation.json')","HERE/(proof+'-validation.json')")
source=source.replace('stage=449','stage=450').replace('actual_448_source_and_artifacts_reused_without_changes=True','only_core_pipeline_changed=True').replace('no_new_core_or_kernel_build=True','incremental_core_build_only=True')
exec(compile(source,str(HERE/'check-inputs.py'),'exec'))
old=json.loads((HERE.parent/'kernel448/build-validation.json').read_text());new=json.loads((HERE/'build-validation.json').read_text())
for row in new['runtime_files']:
 if row['name']!='libcamera.so.0.7.2':assert row==next(v for v in old['runtime_files'] if v['name']==row['name'])
