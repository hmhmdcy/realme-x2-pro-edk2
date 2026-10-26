from pathlib import Path
import difflib,hashlib,json
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel199');fields=['drivers/media/platform/qcom/camss/camss-cpas.c','drivers/media/platform/qcom/camss/camss-cpas.h','drivers/media/platform/qcom/camss/camss.c','arch/arm64/boot/dts/qcom/sm8150.dtsi','Documentation/devicetree/bindings/media/qcom,sm8150-camss.yaml'];original={n:(k/n).read_text() for n in fields};assert hashlib.sha256((k/fields[2]).read_bytes()).hexdigest()=='cc212a4c8674e15fe93a8fba3801fb6850596b7960e1a1df9ab4984ef1633ca2'
for n,s in original.items():p=out/(Path(n).name+'.before199-private');assert not p.exists();p.write_text(s)
s=original[fields[0]].replace('#include <linux/platform_device.h>','#include <linux/platform_device.h>\n#include <linux/pm_domain.h>\n#include <linux/pm_runtime.h>\n#include <dt-bindings/power/qcom,rpmhpd.h>')
s=s.replace('struct camss_cpas {','struct camss_cpas {\n\tstruct device *dev;\n\tstruct device *mmcx;\n\tstruct device_link *mmcx_link;\n\tbool performance_requested;')
marker='int camss_cpas_init(struct camss *camss)'
helpers='''static int camss_cpas_stop(struct camss_cpas *cpas)
{
	int ret;

	if (cpas->performance_requested) {
		ret = dev_pm_genpd_set_performance_state(cpas->mmcx, 0);
		if (ret)
			return ret;
		cpas->performance_requested = false;
	}
	if (cpas->enabled) {
		clk_bulk_disable_unprepare(ARRAY_SIZE(cpas->clocks), cpas->clocks);
		cpas->enabled = false;
	}
	return 0;
}

static void camss_cpas_release(void *data)
{
	struct camss_cpas *cpas = data;
	int ret;

	ret = camss_cpas_stop(cpas);
	if (ret) {
		dev_err(cpas->dev, "failed to release CAMSS MMCX vote: %d\\n", ret);
		if (cpas->enabled)
			clk_bulk_disable_unprepare(ARRAY_SIZE(cpas->clocks), cpas->clocks);
		cpas->enabled = false;
	}
	device_link_del(cpas->mmcx_link);
	dev_pm_domain_detach(cpas->mmcx, true);
}

'''
assert s.count(marker)==1;s=s.replace(marker,helpers+marker)
old='''	camss->cpas = cpas;
	return 0;
}'''
new='''	cpas->dev = dev;
	cpas->mmcx = dev_pm_domain_attach_by_name(dev, "mmcx");
	if (IS_ERR_OR_NULL(cpas->mmcx))
		return dev_err_probe(dev, cpas->mmcx ? PTR_ERR(cpas->mmcx) : -ENODEV,
				     "MMCX power domain is required for camera clocks\\n");
	cpas->mmcx_link = device_link_add(dev, cpas->mmcx,
					DL_FLAG_STATELESS | DL_FLAG_PM_RUNTIME |
					DL_FLAG_RPM_ACTIVE);
	if (!cpas->mmcx_link) {
		dev_pm_domain_detach(cpas->mmcx, true);
		return -EINVAL;
	}
	ret = devm_add_action_or_reset(dev, camss_cpas_release, cpas);
	if (ret)
		return ret;
	camss->cpas = cpas;
	return 0;
}'''
assert s.count(old)==1;s=s.replace(old,new)
start=s.index('int camss_cpas_resume(');stop=s.index('\nvoid camss_cpas_suspend',start);block=s[start:stop]
old='''	ret = clk_set_rate(cpas->clocks[3].clk, 80000000);'''
new='''	/* The resource tables may select 950 MHz: vote before any clock change. */
	ret = dev_pm_genpd_set_performance_state(cpas->mmcx, RPMH_REGULATOR_LEVEL_TURBO);
	if (ret)
		return ret;
	cpas->performance_requested = true;
	ret = clk_set_rate(cpas->clocks[3].clk, 80000000);''';assert block.count(old)==1;block=block.replace(old,new)
needle='''	if (ret)
		return ret;''';assert block.count(needle)==4
# Preserve the performance-request failure; unwind the three later clock failures.
pos=block.index('\tcpas->performance_requested = true;');block=block[:pos]+block[pos:].replace(needle,'''\tif (ret)
		goto reset_performance;''')
old='''	clk_bulk_disable_unprepare(ARRAY_SIZE(cpas->clocks), cpas->clocks);
	return ret;
}''';new='''	clk_bulk_disable_unprepare(ARRAY_SIZE(cpas->clocks), cpas->clocks);
reset_performance:
	if (dev_pm_genpd_set_performance_state(cpas->mmcx, 0))
		dev_err(camss->dev, "failed to unwind CAMSS MMCX vote\\n");
	else
		cpas->performance_requested = false;
	return ret;
}''';assert block.count(old)==1;block=block.replace(old,new)
s=s[:start]+block+'''\nint camss_cpas_suspend(struct camss *camss)
{
	return camss->cpas ? camss_cpas_stop(camss->cpas) : 0;
}
''';modified={fields[0]:s,fields[1]:original[fields[1]].replace('void camss_cpas_suspend(','int camss_cpas_suspend(')}
s=original[fields[2]];start=s.index('static int __maybe_unused camss_runtime_suspend');end=s.index('\nstatic int __maybe_unused camss_runtime_resume',start)
s=s[:start]+'''static int __maybe_unused camss_runtime_suspend(struct device *dev)
{
	struct camss *camss = dev_get_drvdata(dev);
	const struct resources_icc *icc_res = camss->res->icc_res;
	int i, ret;

	for (i = 0; i < camss->res->icc_path_num; i++) {
		ret = icc_set_bw(camss->icc_path[i], 0, 0);
		if (ret)
			goto restore_votes;
	}
	ret = camss_cpas_suspend(camss);
	if (!ret)
		return 0;

restore_votes:
	/* A failed suspend leaves the consumer and its suppliers active. */
	for (i = 0; i < camss->res->icc_path_num; i++)
		if (icc_set_bw(camss->icc_path[i], icc_res[i].icc_bw_tbl.avg,
			       icc_res[i].icc_bw_tbl.peak))
			dev_err(dev, "failed to restore CAMSS interconnect vote\\n");
	return ret;
}
'''+s[end:];modified[fields[2]]=s
s=original[fields[3]];start=s.index('camss: camss@acb3000');end=s.index('\n\t\tcamcc:',start);block=s[start:end];old='''					<&camcc TITAN_TOP_GDSC>;
			power-domain-names = "ife0", "ife1", "top";''';new='''					<&camcc TITAN_TOP_GDSC>,
					<&rpmhpd SM8150_MMCX>;
			power-domain-names = "ife0", "ife1", "top", "mmcx";''';assert block.count(old)==1;modified[fields[3]]=s[:start]+block.replace(old,new)+s[end:]
s=original[fields[4]];s=s.replace('''  power-domains:
    minItems: 3
    maxItems: 3''','''  power-domains:
    items:
      - description: IFE0 power domain
      - description: IFE1 power domain
      - description: TITAN top power domain
      - description: MMCX performance domain for camera clocks''');s=s.replace('''      - const: top
''','''      - const: top
      - const: mmcx
''');modified[fields[4]]=s
patch=''
for n,s in modified.items():
 (k/n).write_text(s);patch+='diff --git a/'+n+' b/'+n+'\n'+''.join(difflib.unified_diff(original[n].splitlines(True),s.splitlines(True),fromfile='a/'+n,tofile='b/'+n))
(ref/'camss-mmcx-runtime.patch').write_text(patch);r=dict(stage=199,source_sha256={n:hashlib.sha256((k/n).read_bytes()).hexdigest() for n in fields},unmodified_frequency_tables=True,mmcx_requested_only_in_camss_runtime_resume=True,normal_runtime_device_link_owns_supplier_reference=True,failed_suspend_keeps_vote_clocks_and_bandwidth=True);(ref/'mmcx-source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
