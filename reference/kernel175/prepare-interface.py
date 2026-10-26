from pathlib import Path
import difflib, hashlib, json, shutil, subprocess

ref=Path(__file__).parent;out=Path('/mnt/e/edk2-samurai-out/kernel175')
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');name='sound/soc/codecs/wcd934x.c'
manifest=json.loads((ref/'source-validation.json').read_text());p=k/name
assert hashlib.sha256(p.read_bytes()).hexdigest()==manifest['source_sha256'][name]
before=out/'before-private'/name;before.parent.mkdir(parents=True,exist_ok=True);assert not before.exists();shutil.copyfile(p,before)
s=p.read_text();old=s
marker='static int wcd934x_codec_parse_data('
s=s.replace(marker,'''static void wcd934x_regmap_exit_action(void *data)
{
	regmap_exit(data);
}

static int wcd934x_init_slim_interface(struct wcd934x_codec *wcd,
				     struct device_node *np)
{
	struct device *dev = wcd->dev;
	int ret;

	wcd->sidev = of_slim_get_device(wcd->sdev->ctrl, np);
	if (!wcd->sidev)
		return dev_err_probe(dev, -EINVAL, "Unable to get SLIM Interface device\\n");

	/* Keep the interface alive until its codec-owned regmap is released. */
	ret = devm_add_action_or_reset(dev, wcd934x_put_device_action,
				       &wcd->sidev->dev);
	if (ret)
		return ret;

	ret = slim_get_logical_addr(wcd->sidev);
	if (ret)
		return dev_err_probe(dev, ret, "Unable to get SLIM Interface address\\n");

	wcd->if_regmap = regmap_init_slimbus(wcd->sidev,
					  &wcd934x_ifc_regmap_config);
	if (IS_ERR(wcd->if_regmap))
		return dev_err_probe(dev, PTR_ERR(wcd->if_regmap),
				     "Failed to allocate ifc register map\\n");

	ret = devm_add_action_or_reset(dev, wcd934x_regmap_exit_action,
				       wcd->if_regmap);
	if (ret)
		wcd->if_regmap = NULL;

	return ret;
}

'''+marker)
a=s.index('static int wcd934x_codec_parse_data(');b=s.index('static int wcd934x_codec_probe(',a)
part=s[a:b].replace('\tstruct device_node *ifc_dev_np;','\tstruct device_node *ifc_dev_np;\n\tint ret;')
start=part.index('\twcd->sidev = of_slim_get_device(');end=part.index('\n\tof_property_read_u32(',start)
part=part[:start]+'''	ret = wcd934x_init_slim_interface(wcd, ifc_dev_np);
	of_node_put(ifc_dev_np);
	if (ret)
		return ret;
'''+part[end:]
s=s[:a]+part+s[b:]
a=s.index('static int wcd934x_codec_probe(')
needle='\tret = devm_add_action_or_reset(dev, wcd934x_put_device_action, &wcd->sidev->dev);\n\tif (ret)\n\t\treturn ret;\n\n'
assert s[a:].count(needle)==1
s=s[:a]+s[a:].replace(needle,'')
p.write_text(s)
manifest['modified_this_stage'].append(name)
manifest['before_sha256'][name]=hashlib.sha256(old.encode()).hexdigest()
manifest['codec_interface_regmap_owned_by_codec_dev_and_exit_before_put']=True
patch=(ref/'card-and-wcd-lifetime.patch').read_text().split('--- a/')[0]
for n in manifest['modified_this_stage']:
    patch+=''.join(difflib.unified_diff((out/'before-private'/n).read_text().splitlines(True),(k/n).read_text().splitlines(True),fromfile='a/'+n,tofile='b/'+n))
(ref/'card-and-wcd-lifetime.patch').write_text(patch)
r=subprocess.run(['scripts/checkpatch.pl','--no-tree','--strict','--no-signoff',str(ref/'card-and-wcd-lifetime.patch')],cwd=k,capture_output=True)
(out/'checkpatch-private.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,r.stdout.decode()
subprocess.run(['git','diff','--check'],cwd=k,check=True)
for n in manifest['source_sha256']:manifest['source_sha256'][n]=hashlib.sha256((k/n).read_bytes()).hexdigest()
for folder in [ref,out]:(folder/'source-validation.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('K175_CODEC_INTERFACE_LIFETIME_PREPARED',flush=True)
