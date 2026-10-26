from pathlib import Path
import difflib, hashlib, json

k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
out=Path('/mnt/e/edk2-samurai-out/kernel166')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel166')
name='sound/soc/codecs/wcd934x.c';p=k/name;old=p.read_text()
backup=out/'wcd934x.c.163-before-private'
assert not backup.exists();backup.write_bytes(p.read_bytes())
def replace(s,a,b):
    assert s.count(a)==1,a
    return s.replace(a,b)
new=replace(old,'\t\tint val;\n\n\t\tregmap_read(wcd->regmap, WCD934X_CDC_CLK_RST_CTRL_SWR_CONTROL,',
                '\t\tint val = 0;\n\n\t\tregmap_read(wcd->regmap, WCD934X_CDC_CLK_RST_CTRL_SWR_CONTROL,')
new=replace(new,'''\tregmap_read(regmap, WCD934X_CHIP_TIER_CTRL_EFUSE_VAL_OUT14, &val1);
\tregmap_read(regmap, WCD934X_CHIP_TIER_CTRL_EFUSE_VAL_OUT15, &val2);''',
'''\tret = regmap_read(regmap, WCD934X_CHIP_TIER_CTRL_EFUSE_VAL_OUT14, &val1);
\tif (ret)
\t\treturn ret;
\tret = regmap_read(regmap, WCD934X_CHIP_TIER_CTRL_EFUSE_VAL_OUT15, &val2);
\tif (ret)
\t\treturn ret;''')
new=replace(new,'static void wcd934x_enable_efuse_sensing(', 'static int wcd934x_enable_efuse_sensing(')
start=new.index('static int wcd934x_enable_efuse_sensing(');end=new.index('\nstatic int wcd934x_swrm_clock',start)
new=new[:start]+'''static int wcd934x_enable_efuse_sensing(struct wcd934x_codec *wcd)
{
\tint ret, val;

\tret = __wcd934x_cdc_mclk_enable(wcd, true);
\tif (ret)
\t\treturn ret;

\tret = regmap_update_bits(wcd->regmap,
\t\t\t\t WCD934X_CHIP_TIER_CTRL_EFUSE_CTL,
\t\t\t\t WCD934X_EFUSE_SENSE_STATE_MASK,
\t\t\t\t WCD934X_EFUSE_SENSE_STATE_DEF);
\tif (ret)
\t\tgoto disable_mclk;
\tret = regmap_update_bits(wcd->regmap,
\t\t\t\t WCD934X_CHIP_TIER_CTRL_EFUSE_CTL,
\t\t\t\t WCD934X_EFUSE_SENSE_EN_MASK,
\t\t\t\t WCD934X_EFUSE_SENSE_ENABLE);
\tif (ret)
\t\tgoto disable_mclk;
\t/*
\t * 5ms sleep required after enabling efuse control
\t * before checking the status.
\t */
\tusleep_range(5000, 5500);
\tret = wcd934x_set_sido_input_src(wcd, SIDO_SOURCE_RCO_BG);
\tif (ret)
\t\tgoto disable_mclk;

\tret = regmap_read(wcd->regmap,
\t\t\t  WCD934X_CHIP_TIER_CTRL_EFUSE_STATUS, &val);
\tif (!ret && !(val & 0x01)) {
\t\tdev_err(wcd->dev, "Efuse sense is not complete: val=%x\\n", val);
\t\tret = -EIO;
\t}

disable_mclk:
\t__wcd934x_cdc_mclk_enable(wcd, false);
\treturn ret;
}
''' + new[end:]
new=replace(new,'''static void wcd934x_hw_init(struct wcd934x_codec *wcd)
{
\tstruct regmap *rm = wcd->regmap;

\t/* set SPKR rate to FS_2P4_3P072 */
\tregmap_update_bits(rm, WCD934X_CDC_RX7_RX_PATH_CFG1, 0x08, 0x08);
\tregmap_update_bits(rm, WCD934X_CDC_RX8_RX_PATH_CFG1, 0x08, 0x08);

\t/* Take DMICs out of reset */
\tregmap_update_bits(rm, WCD934X_CPE_SS_DMIC_CFG, 0x80, 0x00);
}''',
'''static int wcd934x_hw_init(struct wcd934x_codec *wcd)
{
\tstruct regmap *rm = wcd->regmap;
\tint ret;

\t/* set SPKR rate to FS_2P4_3P072 */
\tret = regmap_update_bits(rm, WCD934X_CDC_RX7_RX_PATH_CFG1, 0x08, 0x08);
\tif (ret)
\t\treturn ret;
\tret = regmap_update_bits(rm, WCD934X_CDC_RX8_RX_PATH_CFG1, 0x08, 0x08);
\tif (ret)
\t\treturn ret;

\t/* Take DMICs out of reset */
\treturn regmap_update_bits(rm, WCD934X_CPE_SS_DMIC_CFG, 0x80, 0x00);
}''')
new=replace(new,'''\twcd934x_hw_init(wcd);
\twcd934x_enable_efuse_sensing(wcd);
\twcd934x_get_version(wcd);

\treturn 0;''',
'''\tint ret;

\tret = wcd934x_hw_init(wcd);
\tif (ret)
\t\treturn ret;
\tret = wcd934x_enable_efuse_sensing(wcd);
\tif (ret)
\t\treturn ret;

\treturn wcd934x_get_version(wcd);''')
new=replace(new,'''\t/* Class-H Init*/
\twcd->clsh_ctrl = wcd_clsh_ctrl_alloc(component, wcd->version);''',
'''\tif (READ_ONCE(wcd->sdev->status) != SLIM_DEVICE_STATUS_UP)
\t\treturn -EPROBE_DEFER;

\tret = wcd934x_comp_init(component);
\tif (ret) {
\t\tif (ret == -EREMOTEIO || ret == -ENOTCONN ||
\t\t    ret == -EHOSTDOWN || ret == -EAGAIN)
\t\t\tret = -EPROBE_DEFER;
\t\treturn dev_err_probe(component->dev, ret,
\t\t\t\t     "Failed to initialize WCD934x hardware\\n");
\t}

\t/* Class-H Init*/
\twcd->clsh_ctrl = wcd_clsh_ctrl_alloc(component, wcd->version);''')
new=replace(new,'\twcd934x_comp_init(component);\n\n', '')
new=replace(new,'\t\tdev_err(component->dev, "Failed to Initialize micbias\\n");\n\t\treturn ret;',
                '\t\tdev_err(component->dev, "Failed to Initialize micbias\\n");\n\t\twcd_clsh_ctrl_free(wcd->clsh_ctrl);\n\t\treturn ret;')
p.write_text(new)
patch=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
(ref/'wcd934x-init-errors.patch').write_text(patch)
report=json.loads((ref/'source-validation.json').read_text())
report['modified_files'].append(name);report['source_sha256'][name]=hashlib.sha256(p.read_bytes()).hexdigest()
report.update(codec_init_aborts_bus_down=True, efuse_errors_propagated=True,
              efuse_status_failure_not_treated_as_valid_data=True, class_h_allocated_after_version=True)
for folder in [ref,out]:
    (folder/'source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
