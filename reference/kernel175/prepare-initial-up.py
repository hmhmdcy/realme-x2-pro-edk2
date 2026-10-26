from pathlib import Path
import difflib, hashlib, json, shutil, subprocess

ref=Path(__file__).parent;out=Path('/mnt/e/edk2-samurai-out/kernel175');k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
manifest=json.loads((ref/'source-validation.json').read_text());name='drivers/mfd/wcd934x.c';p=k/name
assert hashlib.sha256(p.read_bytes()).hexdigest()==manifest['source_sha256'][name]
shutil.copyfile(ref/'build-package-validation.json',out/'build-package-validation-v3-private.json')
s=p.read_text()
s=s.replace('\treturn container_of(ddata, struct wcd934x_priv, ddata);','\tif (!ddata)\n\t\treturn NULL;\n\n\treturn container_of(ddata, struct wcd934x_priv, ddata);')
a=s.index('static int wcd934x_slim_status(');b=s.index('static int wcd934x_slim_probe(',a)
part=s[a:b]
part=part.replace('\tmutex_lock(&priv->lock);','\tif (!priv)\n\t\treturn -EPROBE_DEFER;\n\n\tmutex_lock(&priv->lock);')
s=s[:a]+part+s[b:]
marker='static int wcd934x_slim_probe('
s=s.replace(marker,'''static int wcd934x_finish_probe(struct slim_device *sdev)
{
	/* A driver rebind can start while the bus device is already UP. */
	if (sdev->status == SLIM_DEVICE_STATUS_UP)
		return wcd934x_slim_status(sdev, SLIM_DEVICE_STATUS_UP);

	return 0;
}

'''+marker)
needle='\tdev_set_drvdata(dev, ddata);\n\n\treturn 0;'
assert s.count(needle)==1
s=s.replace(needle,'''\tdev_set_drvdata(dev, ddata);
\tret = wcd934x_finish_probe(sdev);
\tif (ret)
\t\tgoto err_disable_regulators;

\treturn 0;''')
p.write_text(s);manifest['source_sha256'][name]=hashlib.sha256(p.read_bytes()).hexdigest()
manifest['already_up_driver_bind_and_early_callback_guard']=True
patch=(ref/'card-and-wcd-lifetime.patch').read_text().split('--- a/')[0]
for n in manifest['modified_this_stage']:
    patch+=''.join(difflib.unified_diff((out/'before-private'/n).read_text().splitlines(True),(k/n).read_text().splitlines(True),fromfile='a/'+n,tofile='b/'+n))
(ref/'card-and-wcd-lifetime.patch').write_text(patch)
r=subprocess.run(['scripts/checkpatch.pl','--no-tree','--strict','--no-signoff',str(ref/'card-and-wcd-lifetime.patch')],cwd=k,capture_output=True)
(out/'checkpatch-private.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,r.stdout.decode()
subprocess.run(['git','diff','--check'],cwd=k,check=True)
for folder in [ref,out]:(folder/'source-validation.json').write_text(json.dumps(manifest,indent=2)+'\n')
s=(ref/'build-package-v3.py').read_text().replace('-v3-build-private.log','-v4-build-private.log').replace('Image-k175-lifetime-v3-private','Image-k175-lifetime-v4-private').replace('logdump-k175-lifetime-v3.img','logdump-k175-lifetime-v4.img').replace('modules-root175-v3','modules-root175-v4')
s=s.replace('card_probe_failure_cleanup_included=True','already_up_bind_fix_included=True,card_probe_failure_cleanup_included=True')
(ref/'build-package-v4.py').write_text(s)
print('K175_ALREADY_UP_BIND_PREPARED',flush=True)
