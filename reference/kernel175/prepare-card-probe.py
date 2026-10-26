from pathlib import Path
import difflib, hashlib, json, shutil, subprocess

ref=Path(__file__).parent;out=Path('/mnt/e/edk2-samurai-out/kernel175');k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
manifest=json.loads((ref/'source-validation.json').read_text());name='sound/soc/qcom/samurai-audio.c';p=k/name
assert hashlib.sha256(p.read_bytes()).hexdigest()==manifest['source_sha256'][name]
shutil.copyfile(ref/'build-package-validation.json',out/'build-package-validation-v2-private.json')
shutil.copyfile(ref/'source-validation.json',out/'source-v2-private.json')
s=p.read_text();marker='static int samurai_card_remove('
s=s.replace(marker,'''static int samurai_card_probe(struct snd_soc_card *card)
{
	struct samurai_audio_data *data = snd_soc_card_get_drvdata(card);

	/* Start the card lifetime before BE init, including failed bindings. */
	data->jack_created = false;
	data->jack_component = NULL;

	return 0;
}

'''+marker)
s=s.replace('\tcard->remove = samurai_card_remove;','\tcard->probe = samurai_card_probe;\n\tcard->remove = samurai_card_remove;')
p.write_text(s);manifest['source_sha256'][name]=hashlib.sha256(p.read_bytes()).hexdigest()
manifest['card_probe_enables_core_remove_on_bind_failures']=True
patch=(ref/'card-and-wcd-lifetime.patch').read_text().split('--- a/')[0]
for n in manifest['modified_this_stage']:
    patch+=''.join(difflib.unified_diff((out/'before-private'/n).read_text().splitlines(True),(k/n).read_text().splitlines(True),fromfile='a/'+n,tofile='b/'+n))
(ref/'card-and-wcd-lifetime.patch').write_text(patch)
r=subprocess.run(['scripts/checkpatch.pl','--no-tree','--strict','--no-signoff',str(ref/'card-and-wcd-lifetime.patch')],cwd=k,capture_output=True)
(out/'checkpatch-private.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,r.stdout.decode()
subprocess.run(['git','diff','--check'],cwd=k,check=True)
for folder in [ref,out]:(folder/'source-validation.json').write_text(json.dumps(manifest,indent=2)+'\n')
s=(ref/'build-package-v2.py').read_text().replace('-v2-build-private.log','-v3-build-private.log').replace('Image-k175-lifetime-v2-private','Image-k175-lifetime-v3-private').replace('logdump-k175-lifetime-v2.img','logdump-k175-lifetime-v3.img').replace('modules-root175','modules-root175-v3')
s=s.replace('clock_lifetime_fix_included=True','card_probe_failure_cleanup_included=True,clock_lifetime_fix_included=True')
(ref/'build-package-v3.py').write_text(s)
print('K175_CARD_PROBE_FAILURE_CLEANUP_PREPARED',flush=True)
