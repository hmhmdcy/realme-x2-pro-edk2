from pathlib import Path
import json
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel222')
state=json.loads((private/'sof-build-state-private.json').read_text());assert state['exit']==2 and state['canonical_sources_objects_metadata_restored']
code=(here/'build-sof-candidate.py').read_text()
code=code.replace("files|={kernel/n for n in", "files|={p for p in (kernel/'drivers/media/common/videobuf2').iterdir() if p.is_file() and not p.is_symlink()}\nfiles|={kernel/n for n in")
code=code.replace("'include/generated/compile.h','include/generated/utsrelease.h'", "'include/generated/compile.h','include/generated/utsrelease.h','include/generated/autoconf.h','include/config/auto.conf','include/config/auto.conf.cmd'")
code=code.replace("snapshot=private/'kernel-before-sof'","snapshot=private/'kernel-before-sof-r2'").replace("private/'sof-build-state-private.json'","private/'sof-build-r2-state-private.json'").replace("private/'sof-kernel-build-private.log'","private/'sof-kernel-build-r2-private.log'")
old="'W=1','-j3','drivers/media/platform/qcom/camss/qcom-camss.ko']"
new="'W=1','-j3',*['drivers/media/common/videobuf2/videobuf2-'+n+'.ko' for n in ['common','memops','v4l2','dma-sg']],'drivers/media/platform/qcom/camss/qcom-camss.ko']"
assert code.count(old)==1;code=code.replace(old,new)
code=code.replace("  for p in media.iterdir():\n   if", "  for p in list(media.iterdir())+list((kernel/'drivers/media/common/videobuf2').iterdir()):\n   if")
code=code.replace('phone_not_yet_modified=True','phone_not_yet_modified=True,dependency_vb2_modules_built_for_modpost=True,initial_missing_dependency_modpost_failure_preserved=True')
compile(code,'build-sof-candidate-r2','exec');(here/'build-sof-candidate-r2.py').write_text(code)
r=dict(stage=222,initial_candidate_compile_succeeded_modpost_failed=True,missing_vb2_dependency_targets=True,original118_files_and_metadata_restored=True,no_device_module_transition=True,resume_adds_four_dependency_targets_and_protects_dependency_objects=True)
(here/'sof-initial-build-failure-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
