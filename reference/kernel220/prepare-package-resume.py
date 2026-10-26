from pathlib import Path
import json,shutil
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel220')
state=json.loads((private/'incremental-build-state-private.json').read_text());assert state['exit']==1 and state['original214_recipe_source_objects_and_metadata_restored']
log=(private/'full-candidate-build-private.log').read_text();assert '[44/44]' in log and 'Directory not empty' in log
shutil.copyfile(private/'incremental-build-state-private.json',private/'initial-rootpkg-failure-state-private.json')
text=(here/'resume-full-candidate.py').read_text()
text=text.replace("snapshot=root/'private/libcamera214-before220-r2'","snapshot=root/'private/libcamera214-before220-r3'")
text=text.replace("and not (root/'packages220').exists()", "and not list((root/'packages220').rglob('*.apk'))")
text=text.replace(' os.rename(retained,work)\n'," os.rename(retained,work)\n assert (work/'pkg').is_dir() and not (work/'pkg-before220-rootpkg-failure').exists()\n os.rename(work/'pkg',work/'pkg-before220-rootpkg-failure')\n")
text=text.replace('build rootpkg index','rootpkg index').replace("full-candidate-build-private.log","candidate-repackage-private.log")
text=text.replace('incremental_full_feature_object_cache_used=True,','incremental_full_feature_object_cache_used=True,completed44_target_build_reused_without_recompilation=True,')
compile(text,'package-resume220-r3','exec');(here/'resume-candidate-packaging.py').write_text(text)
r=dict(stage=220,full_candidate_compilation_completed=True,ninja_targets=44,first_packaging_failed=True,
 reason='Retained old subpackage install directories collided in official rootpkg split; original214 tree restored',
 compiled_candidate_and_failure_logs_retained=True,existing_signed_candidate_apks=0,
 next='Rename only candidate pkg tree aside, reuse completed build and rerun official rootpkg/index; no device changes')
(here/'initial-packaging-failure-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
