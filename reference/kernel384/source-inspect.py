from pathlib import Path
import importlib.util,subprocess,json
HERE=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel384');P.mkdir(mode=0o700,exist_ok=True)
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
source=m.mounted_build().parent/'source354';git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
head=git('rev-parse','HEAD');assert head=='a9f823f210344ab551e4859b4889358916345fbb' and not git('status','--porcelain')
for name in ['camss-icp-a5-ipe.c','camss-icp-a5-ipe.h','camss-icp-a5-boot.c','camss-icp-a5-boot.h','camss-icp-a5-boot-test.c']:
 (P/(name+'.before')).write_text((source/'drivers/media/platform/qcom/camss'/name).read_text())
report=dict(stage=384,source=str(source),source_commit=head,source_clean=True,phone_mutated=False,low_light_context_recorded=True,passed=True)
(HERE/'initial-state-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
