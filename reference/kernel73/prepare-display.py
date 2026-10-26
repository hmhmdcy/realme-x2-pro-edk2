from pathlib import Path
import hashlib, json, shutil, tarfile, struct

root = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel73')
kernel = Path('/home/cy122/x2pro-linux/linux')
out = Path('/mnt/e/edk2-samurai-out/kernel73')
for src, dest in [('.config','config-before'), ('arch/arm64/boot/Image','Image-before'),
                  ('arch/arm64/boot/dts/qcom/sm8150-samurai.dts','dts-before'),
                  ('arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','dtb-before'),
                  ('drivers/gpu/drm/panel/Kconfig','panel-kconfig-before'),
                  ('drivers/gpu/drm/panel/Makefile','panel-makefile-before')]:
    target = out/dest
    assert not target.exists(), target
    shutil.copyfile(kernel/src, target)
core = ['drivers/tty/serial/eud.c','drivers/tty/serial/eud_earlycon.c',
        'drivers/input/rmi4/rmi_i2c.c','drivers/soc/qcom/rpmh-rsc.c']
(root/'core-before.json').write_text(json.dumps({n:hashlib.sha256((kernel/n).read_bytes()).hexdigest()
    for n in core},indent=2)+'\n')

commands = json.loads((root/'live60-on.json').read_text())
assert len(commands) == 51
assert all(c['type'] in (5,21,57) and c['vc']==0 and c['ack']==0 for c in commands)
pps = bytes.fromhex(commands[1]['data'])
assert pps[0]==0x9e and len(pps)==129
body = []
for c in commands:
    data = bytes.fromhex(c['data'])
    if data[0]==0x9e:
        body.append('\tmipi_dsi_dcs_write_buffer_multi(&dsi_ctx, command, sizeof(command));')
    else:
        args = ', '.join('0x%02x'%v for v in data)
        body.append('\tmipi_dsi_dcs_write_seq_multi(&dsi_ctx, '+args+');')
    if c['delay']:
        body.append('\tmipi_dsi_msleep(&dsi_ctx, %d);'%c['delay'])
template = (root/'panel-template.c').read_text()
pps_c = '\n'.join('\t'+', '.join('0x%02x'%v for v in pps[i:i+16])+',' for i in range(1,129,16))
source = template.replace('/* @STOCK_PPS@ */',pps_c).replace('/* @ON_COMMANDS@ */','\n'.join(body))
(kernel/'drivers/gpu/drm/panel/panel-samsung-sofef03f.c').write_text(source)
(root/'panel-samsung-sofef03f.c').write_text(source)
kconfig = kernel/'drivers/gpu/drm/panel/Kconfig'
assert 'DRM_PANEL_SAMSUNG_SOFEF03F' not in kconfig.read_text()
kconfig.write_text(kconfig.read_text()+'''\nconfig DRM_PANEL_SAMSUNG_SOFEF03F
\ttristate "Samsung SOFEF03F_M DSC command mode panel"
\tdepends on OF && GPIOLIB && DRM_MIPI_DSI && BACKLIGHT_CLASS_DEVICE
\tselect DRM_DISPLAY_HELPER
\tselect DRM_DISPLAY_DSC_HELPER
\thelp
\t  Samsung SOFEF03F_M 1080x2400 AMOLED panel in the Realme X2 Pro.
''')
makefile = kernel/'drivers/gpu/drm/panel/Makefile'
makefile.write_text(makefile.read_text()+'obj-$(CONFIG_DRM_PANEL_SAMSUNG_SOFEF03F) += panel-samsung-sofef03f.o\n')

dts = kernel/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'
addition = '''
/* Native display: wiring and rail values verified against stock live DT. */
&mdss {
\tstatus = "okay";
};

&mdss_dsi0 {
\tstatus = "okay";
\tvdda-supply = <&vreg_l3c_1p2>;
\tpinctrl-names = "default";
\tpinctrl-0 = <&display_te_default>;

\tpanel@0 {
\t\tcompatible = "samsung,sofef03f-m";
\t\treg = <0>;
\t\tvddio-supply = <&vreg_l14a_1p8>;
\t\tvdda-supply = <&vreg_l17a_3p0>;
\t\treset-gpios = <&tlmm 6 GPIO_ACTIVE_LOW>;
\t\tvci-enable-gpios = <&tlmm 25 GPIO_ACTIVE_HIGH>;
\t\tvddd-enable-gpios = <&tlmm 152 GPIO_ACTIVE_HIGH>;
\t\tpinctrl-names = "default";
\t\tpinctrl-0 = <&display_reset_default>, <&display_power_default>;
\t\tport {
\t\t\tpanel_in: endpoint {
\t\t\t\tremote-endpoint = <&mdss_dsi0_out>;
\t\t\t};
\t\t};
\t};
};

&mdss_dsi0_out {
\tremote-endpoint = <&panel_in>;
\tdata-lanes = <0 1 2 3>;
};

&mdss_dsi0_phy {
\tstatus = "okay";
\tvdds-supply = <&vreg_l5a_0p875>;
};

&vreg_l14a_1p8 {
\tregulator-min-microvolt = <1800000>;
\tregulator-max-microvolt = <1800000>;
};

&tlmm {
\tdisplay_reset_default: display-reset-default-state {
\t\tpins = "gpio6";
\t\tfunction = "gpio";
\t\tdrive-strength = <8>;
\t\tbias-disable;
\t};
\tdisplay_power_default: display-power-default-state {
\t\tpins = "gpio25", "gpio152";
\t\tfunction = "gpio";
\t\tdrive-strength = <2>;
\t\tbias-disable;
\t};
\tdisplay_te_default: display-te-default-state {
\t\tpins = "gpio8";
\t\tfunction = "mdp_vsync";
\t\tdrive-strength = <2>;
\t\tbias-pull-down;
\t};
};
'''
assert 'samsung,sofef03f-m' not in dts.read_text()
dts.write_text(dts.read_text()+addition)
print('Installed native panel source and DTS; not flashed.')
