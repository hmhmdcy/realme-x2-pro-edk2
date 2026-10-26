from pathlib import Path
import hashlib,json,shutil,subprocess,tempfile
ref=Path(__file__).resolve().parent; workspace=ref.parents[1]
out=Path('/mnt/e/edk2-samurai-out/kernel77'); kernel=Path('/home/cy122/x2pro-linux/linux')
relative=Path('arch/arm64/boot/dts/qcom/sm8150-samurai.dts')
name='0013-arm64-dts-qcom-samurai-bq28z610.patch'
patch=('From: hmhmdcy <hmhmdcy@users.noreply.github.com>\n'
       'Subject: [PATCH] arm64: dts: qcom: samurai: add the stock BQ28Z610 gauge\n\n'
       'The saved Android tree identifies a BQ28Z610 at 0x55 on QUP15. Enable\n'
       'that controller at its stock 100kHz rate and use the existing mainline\n'
       'gauge driver for battery measurements. Do not add charging controllers\n'
       'or battery programming data. This does not implement charging policy.\n\n'
       'Signed-off-by: hmhmdcy <hmhmdcy@users.noreply.github.com>\n\n'+(ref/'gauge-dts.patch').read_text())
target=workspace/'linux-port/patches'/name; target.write_text(patch)
with tempfile.TemporaryDirectory(prefix='k77-gauge-apply-') as directory:
    tree=Path(directory); (tree/relative).parent.mkdir(parents=True)
    shutil.copyfile(out/'dts-before',tree/relative)
    subprocess.run(['git','apply','--check',str(target)],cwd=tree,check=True)
    subprocess.run(['git','apply',str(target)],cwd=tree,check=True)
    assert (tree/relative).read_bytes()==(kernel/relative).read_bytes()
check=subprocess.run(['perl',str(kernel/'scripts/checkpatch.pl'),'--no-tree',str(target)],capture_output=True,text=True)
(ref/(name+'.checkpatch.txt')).write_text(check.stdout+check.stderr)
assert check.returncode==0,check.stdout+check.stderr
shutil.copyfile(kernel/relative,workspace/'linux-port/dts/sm8150-samurai.dts')
report={'exact_apply_pass':True,'checkpatch_exit':check.returncode,'patch_sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
(ref/'patch-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('Exact apply and checkpatch PASS:',name)
