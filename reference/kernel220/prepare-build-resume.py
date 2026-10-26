"""Resume the preserved, already patched candidate after a host path-check error."""
from pathlib import Path
import json,shutil
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel220')
state=json.loads((private/'incremental-build-state-private.json').read_text());assert state['original214_recipe_source_objects_and_metadata_restored'] and 'pid' not in state
shutil.copyfile(private/'incremental-build-state-private.json',private/'initial-sourcecheck-failure-state-private.json')
text=(here/'build-full-candidate.py').read_text()
text=text.replace("snapshot=root/'private/libcamera214-before220'","snapshot=root/'private/libcamera214-before220-r2'")
text=text.replace('not retained.exists() and not (root/\'packages220\').exists()',"retained.exists() and not (root/'packages220').exists()")
begin=text.index(' shutil.copytree(snapshot,work,symlinks=True)');end=text.index(" proof=json.loads((here/'candidate-source-validation.json').read_text())",begin)
text=text[:begin]+" os.rename(retained,work)\n source=work/'src/libcamera-v0.7.2'\n"+text[end:]
text=text.replace("original=inventory(work);(private/'original214-work-manifest-private.json').write_text(json.dumps(original,indent=2)+'\\n')", "original=inventory(work);assert original==json.loads((private/'original214-work-manifest-private.json').read_text())")
assert 'shutil.copytree(snapshot,work' not in text and "'0013-simple-refresh-sensor-timing.patch']" not in text
compile(text,'resume-full-candidate220-r2','exec');(here/'resume-full-candidate.py').write_text(text)
r=dict(stage=220,initial_build_preflight_failed=True,reason='Host followed an absolute chroot distfile symlink outside the SDK root',
 actual_cached_archive_matches_declared_upstream_sha512=True,no_compiler_or_phone_transition_started=True,
 original214_tree_was_restored=True,already_patched_candidate_preserved_and_will_be_resumed=True)
(here/'initial-build-preflight-failure-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
