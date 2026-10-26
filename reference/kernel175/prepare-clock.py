from pathlib import Path
import difflib, hashlib, json, shutil, subprocess

ref=Path(__file__).parent;out=Path('/mnt/e/edk2-samurai-out/kernel175');k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
manifest=json.loads((ref/'source-validation.json').read_text());name='sound/soc/codecs/wcd934x.c';p=k/name
assert hashlib.sha256(p.read_bytes()).hexdigest()==manifest['source_sha256'][name]
shutil.copyfile(ref/'host-tests-validation.json',ref/'host-tests-validation-before-clock.json')
shutil.copyfile(ref/'source-validation.json',out/'source-before-clock-private.json')
s=p.read_text();a=s.index('static struct clk *wcd934x_register_mclk_output(');b=s.index('static int wcd934x_init_dmic(',a)
part=s[a:b].replace('static struct clk *wcd934x_register_mclk_output(','static int wcd934x_register_mclk_output(')
part=part.replace('return NULL;','return 0;').replace('devm_clk_hw_register(wcd->dev->parent, hw)','devm_clk_hw_register(dev, hw)').replace('return ERR_PTR(ret);','return ret;')
s=s[:a]+part+s[b:]
needle='\twcd934x_register_mclk_output(wcd);'
assert s.count(needle)==1
s=s.replace(needle,'''\tret = wcd934x_register_mclk_output(wcd);
\tif (ret)
\t\treturn dev_err_probe(dev, ret, "Failed to register MCLK output\\n");''')
p.write_text(s)
manifest['codec_mclk_hw_and_provider_owned_by_codec_and_errors_propagated']=True
manifest['source_sha256'][name]=hashlib.sha256(p.read_bytes()).hexdigest()
patch=(ref/'card-and-wcd-lifetime.patch').read_text().split('--- a/')[0]
for n in manifest['modified_this_stage']:
    patch+=''.join(difflib.unified_diff((out/'before-private'/n).read_text().splitlines(True),(k/n).read_text().splitlines(True),fromfile='a/'+n,tofile='b/'+n))
(ref/'card-and-wcd-lifetime.patch').write_text(patch)
r=subprocess.run(['scripts/checkpatch.pl','--no-tree','--strict','--no-signoff',str(ref/'card-and-wcd-lifetime.patch')],cwd=k,capture_output=True)
(out/'checkpatch-private.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,r.stdout.decode()
subprocess.run(['git','diff','--check'],cwd=k,check=True)
for folder in [ref,out]:(folder/'source-validation.json').write_text(json.dumps(manifest,indent=2)+'\n')
failure=dict(stage=175,first_build_audio_objects_and_full_image_passed=True,first_packaging_stopped_before_module_install=True,
 reason='copied template retained modules-root174; pre-existing-directory assertion prevented writing',old_module_tree_not_modified=True,
 first_image_preserved_privately_and_not_deployed=True,clock_ownership_change_added_after_first_build=True,second_build_pending=True)
for folder in [ref,out]:(folder/'first-build-rejected.json').write_text(json.dumps(failure,indent=2)+'\n')
print('K175_CLOCK_LIFETIME_PREPARED',flush=True)
