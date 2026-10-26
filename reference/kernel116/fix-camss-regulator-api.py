from pathlib import Path
import shutil,difflib,subprocess
k=Path('/home/cy122/pmos-samurai-kernel116/kernel')
out=Path('/mnt/e/edk2-samurai-out/kernel116')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel116')
shutil.copyfile(out/'camss-targeted-build.log',out/'camss-targeted-first-failure.log')
p=k/'drivers/media/platform/qcom/camss/camss.c';t=p.read_text()
start=t.index('static const struct camss_subdev_resources csid_res_8150[]')
end=t.index('static const struct camss_subdev_resources vfe_res_8150[]')
piece=t[start:end]
assert piece.count('.regulators = { "vdda-phy", "vdda-pll" },')==2
piece=piece.replace('.regulators = { "vdda-phy", "vdda-pll" },','.regulators = {\n\t\t\t{ .supply = "vdda-phy", .init_load_uA = 0 },\n\t\t\t{ .supply = "vdda-pll", .init_load_uA = 0 }\n\t\t},')
p.write_text(t[:start]+piece+t[end:])
before=(out/'camss-base-before.c').read_text();after=p.read_text()
(ref/'camss-base-7.3.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/drivers/media/platform/qcom/camss/camss.c',tofile='b/drivers/media/platform/qcom/camss/camss.c')))
subprocess.run(['git','diff','--check','--','drivers/media/platform/qcom/camss'],cwd=k,check=True)
print('7.3 regulator_bulk_data initializer adapted; original compile failure retained')
