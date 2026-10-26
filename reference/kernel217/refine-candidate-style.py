from pathlib import Path
import difflib,hashlib,json,shutil,subprocess
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel217');candidate=private/'candidate-source';snapshot=private/'candidate-source-r1';snapshot.mkdir(mode=0o700)
for path in candidate.iterdir():shutil.copyfile(path,snapshot/path.name)
shutil.copyfile(here/'factory-mode-candidate-source-validation.json',snapshot/'source-validation.json');shutil.copyfile(here/'factory-mode-candidate-build-validation.json',private/'candidate-build-r2-validation-private.json')
source=candidate/'imx471.c';lines=source.read_text().splitlines(True);changed=0
for index,line in enumerate(lines):
    if line.startswith('                                  const struct imx471_mode *mode)') or line.startswith('                                                u32 width, u32 height)'):
        column=lines[index-1].index('(')+1;lines[index]='\t'*(column//8)+' '*(column%8)+line.lstrip();changed+=1
assert changed==2;source.write_text(''.join(lines))
kernel=Path('/home/cy122/pmos-samurai-kernel136/kernel');patch='media: i2c: imx471: prepare own-handset factory mode candidate\n\nAdd verified mode records and firmware-gated link-frequency selection.\nRetain the legacy preview and expose digital compose geometry.\nFull-resolution quad RAW requires explicit experiment opt-in; full RGB\nremosaic is unfinished.\nThis candidate is not installed and does not claim mode timing acceptance.\n\n---\n'
for original,new,name in [(kernel/'drivers/media/i2c/imx471.c',source,'drivers/media/i2c/imx471.c'),(kernel/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts',candidate/'sm8150-samurai.dts','arch/arm64/boot/dts/qcom/sm8150-samurai.dts')]:patch+=''.join(difflib.unified_diff(original.read_text().splitlines(True),new.read_text().splitlines(True),fromfile='a/'+name,tofile='b/'+name))
(here/'imx471-factory-modes-candidate.patch').write_text(patch)
report=json.loads((here/'factory-mode-candidate-source-validation.json').read_text());report.update(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),candidate_revision=2,checkpatch_tabs_and_description_repaired=True)
(here/'factory-mode-candidate-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
p=subprocess.run(['perl',str(kernel/'scripts/checkpatch.pl'),'--no-tree','--no-signoff',str(here/'imx471-factory-modes-candidate.patch')],capture_output=True,text=True,timeout=45);(private/'candidate-checkpatch-r2-private.log').write_text(p.stdout+p.stderr);assert p.returncode==0
(here/'candidate-style-validation.json').write_text(json.dumps(dict(stage=217,checkpatch_passed=True,errors=0,warnings=0,candidate_not_installed=True),indent=2)+'\n');print('Candidate checkpatch passed: zero errors/warnings; source revision2 ready to rebuild')
