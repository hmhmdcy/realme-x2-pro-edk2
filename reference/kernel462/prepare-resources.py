"""Prepare isolated shared-camera resource changes; no device/build operations."""
from pathlib import Path
import hashlib
import difflib
import importlib.util
import json
import os
import shutil
import subprocess
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('resources_storage449',HERE.parent/'kernel449/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
BUILD=storage.mount.mounted_build();SOURCE=BUILD.parent/'source354'
OUT=Path('/mnt/e/edk2-samurai-out/kernel462');OUT.mkdir(mode=0o700,parents=True,exist_ok=True)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(name,value):(OUT/name).write_text(json.dumps(value,indent=2)+'\n')

def inspect():
    free=dict(ext4_free_bytes=shutil.disk_usage(SOURCE).free,private_free_bytes=shutil.disk_usage(OUT).free)
    assert min(free.values())>1024**3,'Insufficient margin for isolated source copies'
    names=['drivers/media/i2c/imx471.c','arch/arm64/boot/dts/qcom/sm8150-samurai.dts',
       'drivers/mux/core.c','drivers/mux/gpio.c','drivers/mux/Kconfig','drivers/mux/Makefile',
       'drivers/reset/core.c','drivers/reset/reset-gpio.c','include/linux/reset.h','include/linux/mux/consumer.h',
       'drivers/base/pinctrl.c','drivers/base/dd.c','drivers/pinctrl/core.c',
       'Documentation/devicetree/bindings/mux/gpio-mux.yaml','Documentation/devicetree/bindings/mux/mux-controller.yaml',
       'Documentation/devicetree/bindings/media/i2c/sony,imx471.yaml','include/dt-bindings/mux/mux.h']
    rows=[]
    for relative in names:
        path=SOURCE/relative
        if not path.exists():rows.append(dict(path=relative,exists=False));continue
        raw=path.read_bytes();dest=OUT/'original'/relative;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
        rows.append(dict(path=relative,exists=True,bytes=len(raw),sha256=sha(path)))
    write('source-inspection-private.json',dict(source=str(SOURCE),head=subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD']).decode().strip(),free=free,files=rows))
    print(json.dumps(dict(guarded=True,free_gib={k:round(v/1024**3,2) for k,v in free.items()},files=sum(r['exists'] for r in rows))))

SHARED_CODE=r'''/* Shared-route boards never use the legacy direct GPIO/pinctrl path. */
static int imx471_route_get(struct imx471 *sensor)
{
	int ret;

	if (!sensor->route || sensor->route_selected)
		return 0;
	ret = mux_state_try_select(sensor->route);
	if (!ret)
		sensor->route_selected = true;
	return ret;
}

static void imx471_route_put(void *data)
{
	struct imx471 *sensor = data;

	if (!sensor->route_selected)
		return;
	/* A failed shutdown must not hand live shared resources to a peer. */
	if (WARN_ON(sensor->supply_mask || sensor->clock_enabled ||
		    sensor->reset_acquired)) {
		dev_err(sensor->dev, "shared shutdown incomplete; route remains locked\n");
		return;
	}
	if (mux_state_deselect(sensor->route))
		dev_err(sensor->dev, "failed to leave shared route idle\n");
	sensor->route_selected = false;
}

static int imx471_shared_power_off(struct imx471 *sensor)
{
	static const unsigned int order[] = { IMX471_VDIG, IMX471_VANA, IMX471_VIF };
	unsigned int i;
	int ret;

	if (sensor->clock_enabled) {
		clk_disable_unprepare(sensor->img_clk);
		sensor->clock_enabled = false;
	}
	if (sensor->reset_acquired) {
		ret = reset_control_assert(sensor->reset);
		if (ret)
			return ret;
	}
	for (i = 0; i < ARRAY_SIZE(order); i++) {
		unsigned int id = order[i];

		if (!(sensor->supply_mask & BIT(id)))
			continue;
		ret = regulator_disable(sensor->supplies[id].consumer);
		if (ret)
			return ret;
		sensor->supply_mask &= ~BIT(id);
	}
	if (sensor->reset_acquired) {
		reset_control_release(sensor->reset);
		sensor->reset_acquired = false;
	}
	imx471_route_put(sensor);
	return 0;
}

static int imx471_shared_power_on(struct imx471 *sensor)
{
	static const unsigned int order[] = { IMX471_VIF, IMX471_VANA, IMX471_VDIG };
	unsigned int i;
	int ret, cleanup;

	if (sensor->supply_mask || sensor->clock_enabled || sensor->reset_acquired)
		return -EIO;
	ret = imx471_route_get(sensor);
	if (ret)
		return ret;
	ret = reset_control_acquire(sensor->reset);
	if (ret)
		goto error_power_off;
	sensor->reset_acquired = true;
	ret = reset_control_assert(sensor->reset);
	if (ret)
		goto error_power_off;
	ret = clk_set_rate(sensor->img_clk, IMX471_EXT_CLK);
	if (ret)
		goto error_power_off;
	for (i = 0; i < ARRAY_SIZE(order); i++) {
		unsigned int id = order[i];

		ret = regulator_enable(sensor->supplies[id].consumer);
		if (ret)
			goto error_power_off;
		sensor->supply_mask |= BIT(id);
		usleep_range(1000, 2000);
	}
	ret = clk_prepare_enable(sensor->img_clk);
	if (ret)
		goto error_power_off;
	sensor->clock_enabled = true;
	ret = reset_control_deassert(sensor->reset);
	if (ret)
		goto error_power_off;
	usleep_range(10000, 15000);
	return 0;

error_power_off:
	cleanup = imx471_shared_power_off(sensor);
	if (cleanup)
		dev_err(sensor->dev, "shared power-on unwind failed: %d\n", cleanup);
	return ret;
}

static int imx471_init_shared_route(struct imx471 *sensor)
{
	int ret;

	if (!device_property_present(sensor->dev, "mux-states"))
		return 0;
	if (!dev_of_node(sensor->dev))
		return -EINVAL;
#if IS_ENABLED(CONFIG_MULTIPLEXER)
	sensor->route = devm_mux_state_get(sensor->dev, "csi-route");
	if (IS_ERR(sensor->route))
		return PTR_ERR(sensor->route);
#else
	return -EOPNOTSUPP;
#endif
	ret = imx471_route_get(sensor);
	if (ret)
		return ret == -EBUSY ? -EPROBE_DEFER : ret;
	return devm_add_action_or_reset(sensor->dev, imx471_route_put, sensor);
}

'''

def generate():
    original=OUT/'original';candidate=OUT/'candidate'
    relative='drivers/media/i2c/imx471.c'
    text=(original/relative).read_text()
    def replace(old,new):
        nonlocal text
        assert text.count(old)==1,old[:80]
        text=text.replace(old,new)
    replace('#include <linux/module.h>','#include <linux/module.h>\n#include <linux/mux/consumer.h>')
    replace('#include <linux/regulator/consumer.h>','#include <linux/regulator/consumer.h>\n#include <linux/reset.h>\n#include <linux/property.h>')
    replace('\tstruct gpio_desc *reset_gpio;','\tstruct gpio_desc *reset_gpio;\n\tstruct reset_control *reset;\n\tstruct mux_state *route;\n\tunsigned long supply_mask;\n\tbool route_selected;\n\tbool reset_acquired;\n\tbool clock_enabled;')
    replace('static int imx471_power_off(struct device *dev)',SHARED_CODE+'static int imx471_power_off(struct device *dev)')
    off='\tclk_disable_unprepare(sensor->img_clk);\n\tgpiod_set_value_cansleep(sensor->reset_gpio, 1);'
    replace(off,'\tif (sensor->route)\n\t\treturn imx471_shared_power_off(sensor);\n\n'+off)
    replace('\tret = pinctrl_pm_select_default_state(dev);','\tif (sensor->route)\n\t\treturn imx471_shared_power_on(sensor);\n\n\tret = pinctrl_pm_select_default_state(dev);')
    replace('\tif (clk_get_rate(clk) != IMX471_EXT_CLK)','\t/* Shared clocks may only be changed while holding the route lease. */\n\tif (sensor->route) {\n\t\tret = clk_set_rate(clk, IMX471_EXT_CLK);\n\t\tif (ret)\n\t\t\treturn dev_err_probe(sensor->dev, ret, "failed to set shared clock\\n");\n\t}\n\n\tif (clk_get_rate(clk) != IMX471_EXT_CLK)')
    replace('\tsensor->dev = &client->dev;','\tsensor->dev = &client->dev;\n\n\tret = imx471_init_shared_route(sensor);\n\tif (ret)\n\t\treturn dev_err_probe(sensor->dev, ret, "failed to acquire shared route\\n");')
    old='\tsensor->reset_gpio = devm_gpiod_get_optional(sensor->dev, "reset",\n\t\t\t\t\t\t     GPIOD_OUT_HIGH);\n\tif (IS_ERR(sensor->reset_gpio))\n\t\treturn dev_err_probe(sensor->dev, PTR_ERR(sensor->reset_gpio),\n\t\t\t\t     "failed to get reset gpio\\n");'
    new='''\tif (sensor->route) {
\t\t/* reset-gpios fallback deduplicates the shared GPIO provider. */
\t\tsensor->reset = devm_reset_control_get_exclusive_released(sensor->dev, NULL);
\t\tif (IS_ERR(sensor->reset))
\t\t\treturn dev_err_probe(sensor->dev, PTR_ERR(sensor->reset),
\t\t\t\t\t     "failed to get shared reset\\n");
\t} else {
'''+''.join('\t'+line+'\n' for line in old.splitlines())+'\t}'
    replace(old,new)
    replace('\t\tpm_runtime_set_suspended(&client->dev);','\t\tif (sensor->route && sensor->route_selected)\n\t\t\tdev_err(&client->dev, "remove left shared route locked after shutdown failure\\n");\n\t\telse\n\t\t\tpm_runtime_set_suspended(&client->dev);')
    replace('\tstruct v4l2_subdev *sd = i2c_get_clientdata(client);\n\n\tv4l2_async_unregister_subdev(sd);','\tstruct v4l2_subdev *sd = i2c_get_clientdata(client);\n\tstruct imx471 *sensor = to_imx471(sd);\n\n\tv4l2_async_unregister_subdev(sd);')
    replace('\tif (!pm_runtime_status_suspended(&client->dev)) {','\tif (!pm_runtime_status_suspended(&client->dev) ||\n\t    (sensor->route && sensor->route_selected)) {')
    replace('\tpm_runtime_disable(sensor->dev);\n\tpm_runtime_set_suspended(sensor->dev);','\tpm_runtime_disable(sensor->dev);')
    replace('error_power_off:\n\timx471_power_off(sensor->dev);\n\n\treturn ret;','error_power_off:\n\tif (!imx471_power_off(sensor->dev))\n\t\tpm_runtime_set_suspended(sensor->dev);\n\telse\n\t\tdev_err(sensor->dev, "probe shutdown incomplete; routed candidate must not be deployed\\n");\n\n\treturn ret;')
    path=candidate/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
    relative='arch/arm64/boot/dts/qcom/sm8150-samurai.dts';text=(original/relative).read_text()
    begin=text.index('&tlmm {\n\tcam_front_mclk_active:');end=text.index('&cci1 {',begin)
    text=text[:begin]+'''/* Provider bootstrap requires every legacy sensor consumer to be stopped.
 * Shared pin configuration is permanent; only clock gates change at runtime.
 */
&tlmm {
\tcam_front_mono_mclk: camera-front-mono-mclk-state {
\t\tpins = "gpio15";
\t\tfunction = "cam_mclk";
\t\tdrive-strength = <2>;
\t\tbias-disable;
\t};

\tcam_front_mono_gpio: camera-front-mono-gpio-state {
\t\tpins = "gpio29", "gpio12";
\t\tdrive-strength = <2>;
\t\tbias-disable;
\t};
};

/ {
\tcam_front_mono_route: camera-route-mux {
\t\tcompatible = "gpio-mux";
\t\t#mux-state-cells = <1>;
\t\tmux-gpios = <&tlmm 29 GPIO_ACTIVE_HIGH>;
\t\t/* Leave the route unchanged when the last powered consumer exits. */
\t\tpinctrl-names = "default";
\t\tpinctrl-0 = <&cam_front_mono_mclk &cam_front_mono_gpio>;
\t};
};

'''+text[end:]
    old='\t\tassigned-clocks = <&camcc CAM_CC_MCLK2_CLK>;\n\t\tassigned-clock-rates = <19200000>;'
    assert text.count(old)==1;text=text.replace(old,'\t\tmux-states = <&cam_front_mono_route 1>;\n\t\tmux-state-names = "csi-route";')
    old='\t\tpinctrl-names = "default", "sleep";\n\t\tpinctrl-0 = <&cam_front_mclk_active &cam_front_select_active &cam_front_reset>;\n\t\tpinctrl-1 = <&cam_front_mclk_sleep &cam_front_select_sleep &cam_front_reset>;'
    assert text.count(old)==1;text=text.replace(old,'\t\t/* No per-sensor shared pinctrl or automatic assigned-clock changes. */')
    path=candidate/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
    relative='Documentation/devicetree/bindings/media/i2c/sony,imx471.yaml';text=(original/relative).read_text()
    text=text.replace('  port:\n','''  mux-states:
    description: CSI route held exclusively over the complete powered interval.
    maxItems: 1

  mux-state-names:
    items:
      - const: csi-route

  port:
''',1)
    text=text.replace('  - $ref: /schemas/media/video-interface-devices.yaml#','''  - $ref: /schemas/media/video-interface-devices.yaml#
  - if:
      required: [mux-states]
    then:
      required: [mux-state-names, reset-gpios]
      properties:
        pinctrl-names: false
        pinctrl-0: false
        pinctrl-1: false
        assigned-clocks: false
        assigned-clock-rates: false''')
    path=candidate/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
    patch=[];rows=[]
    for path in sorted(candidate.rglob('*')):
        if not path.is_file():continue
        relative=path.relative_to(candidate).as_posix();old=original/relative
        patch.extend(difflib.unified_diff(old.read_text().splitlines(True),path.read_text().splitlines(True),fromfile='a/'+relative,tofile='b/'+relative))
        rows.append(dict(path=relative,original_sha256=sha(old),candidate_sha256=sha(path)))
    (HERE/'0001-media-imx471-use-shared-route-and-reset.patch').write_text(''.join(patch))
    write('candidate-manifest-private.json',dict(files=rows,compiled=False,device_or_dt_deployed=False))
    print(json.dumps(dict(candidate_files=len(rows),patch='0001-media-imx471-use-shared-route-and-reset.patch',compiled=False)))

if __name__=='__main__':
    if sys.argv[1:]==['--inspect']:inspect()
    elif sys.argv[1:]==['--generate']:generate()
    else:raise SystemExit('Use --inspect; no compilation or device calls')
