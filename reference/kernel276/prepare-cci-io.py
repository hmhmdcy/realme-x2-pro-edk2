"""Make shared I2C I/O power a CCI bus resource, without adding lens-specific exceptions."""
from pathlib import Path
import hashlib,json,subprocess
import host
R=Path(__file__).resolve().parent;W=Path('/home/cy122/x2pro-linux/camera270-kernel')
git=lambda *args:subprocess.check_output(['git','-C',str(W),*args],text=True).strip()
assert git('status','--porcelain')=='' and git('rev-parse','HEAD')=='0798ee688921b987a67c045afeab093f9b0c274d'
assert json.loads((R.parent/'kernel275/lens-shared-io-validation.json').read_text())['lens_open_exit']==0
assert json.loads((R.parent/'kernel275/lens-cci-held-validation.json').read_text())['lens_open_exit']!=0
subprocess.run(['git','-C',str(W),'switch','-c','samurai-cci-io276'],check=True)
paths=['drivers/i2c/busses/i2c-qcom-cci.c','Documentation/devicetree/bindings/i2c/qcom,i2c-cci.yaml','arch/arm64/boot/dts/qcom/sm8150-samurai.dts'];before={n:(W/n).read_text() for n in paths};after=dict(before)
def change(name,old,new):assert after[name].count(old)==1,(name,old);after[name]=after[name].replace(old,new)
c=paths[0]
change(c,'#include <linux/pm_runtime.h>','#include <linux/pm_runtime.h>\n#include <linux/regulator/consumer.h>')
change(c,'\tint nclocks;\n\tstruct cci_master master[NUM_MASTERS];','\tint nclocks;\n\tstruct regulator *vddio;\n\tbool io_enabled;\n\tbool clocks_enabled;\n\tstruct cci_master master[NUM_MASTERS];')
old='''static int cci_enable_clocks(struct cci *cci)
{
\treturn clk_bulk_prepare_enable(cci->nclocks, cci->clocks);
}

static void cci_disable_clocks(struct cci *cci)
{
\tclk_bulk_disable_unprepare(cci->nclocks, cci->clocks);
}'''
new='''static int cci_enable_clocks(struct cci *cci)
{
\tint ret;

\tif (cci->clocks_enabled)
\t\treturn 0;
\tret = clk_bulk_prepare_enable(cci->nclocks, cci->clocks);
\tif (!ret)
\t\tcci->clocks_enabled = true;
\treturn ret;
}

static void cci_disable_clocks(struct cci *cci)
{
\tif (!cci->clocks_enabled)
\t\treturn;
\tclk_bulk_disable_unprepare(cci->nclocks, cci->clocks);
\tcci->clocks_enabled = false;
}

static int cci_enable_io(struct cci *cci)
{
\tint ret;

\tif (!cci->vddio || cci->io_enabled)
\t\treturn 0;
\tret = regulator_enable(cci->vddio);
\tif (!ret)
\t\tcci->io_enabled = true;
\treturn ret;
}

static int cci_disable_io(struct cci *cci)
{
\tint ret;

\tif (!cci->io_enabled)
\t\treturn 0;
\tret = regulator_disable(cci->vddio);
\tif (!ret)
\t\tcci->io_enabled = false;
\treturn ret;
}

static void cci_release_power(void *data)
{
\tstruct cci *cci = data;
\tint ret;

\tret = cci_disable_io(cci);
\tif (ret)
\t\tdev_err(cci->dev, "failed to release I/O supply: %d\\n", ret);
\tcci_disable_clocks(cci);
}'''
change(c,old,new)
old='''\tstruct cci *cci = dev_get_drvdata(dev);

\tcci_disable_clocks(cci);
\treturn 0;
}

static int __maybe_unused cci_resume_runtime'''
new='''\tstruct cci *cci = dev_get_drvdata(dev);
\tint ret;

\t/* Keep the active clock state if the supply cannot be released. */
\tret = cci_disable_io(cci);
\tif (ret)
\t\treturn ret;
\tcci_disable_clocks(cci);
\treturn 0;
}

static int __maybe_unused cci_resume_runtime'''
change(c,old,new)
old='''\tret = cci_enable_clocks(cci);
\tif (ret)
\t\treturn ret;

\tcci_init(cci);'''
new='''\tret = cci_enable_io(cci);
\tif (ret)
\t\treturn ret;
\tret = cci_enable_clocks(cci);
\tif (ret) {
\t\tint cleanup = cci_disable_io(cci);

\t\tif (cleanup)
\t\t\tdev_err(dev, "failed to release I/O after clock error: %d\\n",
\t\t\t\tcleanup);
\t\treturn ret;
\t}

\tcci_init(cci);'''
change(c,old,new)
anchor='''\tif (!cci->data)
\t\treturn -ENOENT;
'''
change(c,anchor,anchor+'''
\tcci->vddio = devm_regulator_get_optional(dev, "vddio");
\tif (IS_ERR(cci->vddio)) {
\t\tret = PTR_ERR(cci->vddio);
\t\tif (ret != -ENODEV)
\t\t\treturn dev_err_probe(dev, ret, "failed to get I/O supply\\n");
\t\tcci->vddio = NULL;
\t}
''')
anchor='''\tcci->nclocks = ret;

\tret = cci_enable_clocks(cci);'''
change(c,anchor,'''\tcci->nclocks = ret;

\t/* Registered before IRQ and runtime PM cleanup, so those unwind first. */
\tret = devm_add_action_or_reset(dev, cci_release_power, cci);
\tif (ret)
\t\treturn ret;
\tret = cci_enable_io(cci);
\tif (ret)
\t\treturn ret;
\tret = cci_enable_clocks(cci);''')
old='''\tstruct cci *cci = platform_get_drvdata(pdev);
\tint i;

\tfor (i = 0; i < cci->data->num_masters; i++) {
\t\tif (cci->master[i].cci) {
\t\t\ti2c_del_adapter(&cci->master[i].adap);
\t\t\tcci_halt(cci, i);
\t\t}
\t}
}'''
new='''\tstruct cci *cci = platform_get_drvdata(pdev);
\tint i, ret;

\t/* Do not access halt registers while the controller is suspended. */
\tret = pm_runtime_resume_and_get(cci->dev);
\tif (ret < 0)
\t\tdev_warn(cci->dev, "failed to resume for removal: %d\\n", ret);
\tfor (i = 0; i < cci->data->num_masters; i++) {
\t\tif (cci->master[i].cci) {
\t\t\ti2c_del_adapter(&cci->master[i].adap);
\t\t\tif (ret >= 0)
\t\t\t\tcci_halt(cci, i);
\t\t}
\t}
\tif (ret >= 0)
\t\tpm_runtime_put_noidle(cci->dev);
}'''
change(c,old,new)
anchor='''\t\tret = i2c_add_adapter(&cci->master[i].adap);
\t\tif (ret < 0)
\t\t\tgoto error_i2c;
\t}

\treturn 0;'''
change(c,anchor,'''\t\tret = i2c_add_adapter(&cci->master[i].adap);
\t\tif (ret < 0)
\t\t\tgoto error_i2c;
\t}

\tpm_runtime_mark_last_busy(dev);
\tpm_runtime_idle(dev);
\treturn 0;''')
change(paths[1],'  reg:\n    maxItems: 1\n','  reg:\n    maxItems: 1\n\n  vddio-supply:\n    description: Supply for the shared CCI I2C bus I/O and pull-ups.\n')
# This is handset wiring, not a voltage or PMIC phandle in the SM8150 SoC file.
after[paths[2]]+='\n/* Shared camera I/O must also be powered for autonomous lens/EEPROM traffic. */\n&cci0 {\n\tvddio-supply = <&vreg_l1c_1p8>;\n};\n\n&cci1 {\n\tvddio-supply = <&vreg_l1c_1p8>;\n};\n'
for name,text in after.items():p=W/name;p.write_text(text)
shas={n:hashlib.sha256(t.encode()).hexdigest() for n,t in after.items()}
for name,text in after.items():(R/Path(name).name).write_text(text)
out=dict(stage=276,base=git('rev-parse','HEAD'),branch=git('branch','--show-current'),source_files_sha256=shas,
 no_soc_power_domain_change_needed=True,shared_io_on_board_cci_nodes=True,no_lens_model_or_address_conditionals=True,not_built_or_deployed=True,
 hypothesis_shared_io_dependency=True,physical_vio_only_intervention_not_yet_verified=True)
(R/'source-candidate-validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
