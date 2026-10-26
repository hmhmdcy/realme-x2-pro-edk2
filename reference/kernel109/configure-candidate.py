from pathlib import Path
import hashlib, json, shutil, subprocess

ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel109')
out=Path('/mnt/e/edk2-samurai-out/kernel109')
stage=Path('/home/cy122/pmos-samurai-kernel109')
k=stage/'kernel'; init=stage/'initramfs'; root=stage/'rootfs'
path=k/'drivers/gpu/drm/panel/panel-samsung-sofef03f.c'
original=path.read_text(); s=original
s=s.replace('\tstruct gpio_desc *vddd;\n','\tstruct gpio_desc *vddd;\n\tbool supply_enabled[2];\n')
needle='static void sofef03f_power_off(struct sofef03f *ctx)'
helper='''/* Keep our regulator references balanced even when disable fails. */
static int sofef03f_supply_enable(struct sofef03f *ctx, unsigned int index)
{
\tint ret;

\tif (ctx->supply_enabled[index])
\t\treturn 0;
\tret = regulator_enable(ctx->supplies[index].consumer);
\tif (!ret)
\t\tctx->supply_enabled[index] = true;
\treturn ret;
}

static void sofef03f_supply_disable(struct sofef03f *ctx, unsigned int index)
{
\tint ret;

\tif (!ctx->supply_enabled[index])
\t\treturn;
\tret = regulator_disable(ctx->supplies[index].consumer);
\tif (ret)
\t\tdev_err(&ctx->dsi->dev, "Failed to disable %s: %d\\n",
\t\t\tctx->supplies[index].supply, ret);
\telse
\t\tctx->supply_enabled[index] = false;
}

'''
assert s.count(needle)==1; s=s.replace(needle,helper+needle)
s=s.replace('regulator_disable(ctx->supplies[1].consumer);','sofef03f_supply_disable(ctx, 1);')
s=s.replace('regulator_disable(ctx->supplies[0].consumer);','sofef03f_supply_disable(ctx, 0);')
s=s.replace('regulator_enable(ctx->supplies[0].consumer)','sofef03f_supply_enable(ctx, 0)')
s=s.replace('regulator_enable(ctx->supplies[1].consumer)','sofef03f_supply_enable(ctx, 1)')
old='''\tmipi_dsi_dcs_set_display_off_multi(&dsi_ctx);
\tmipi_dsi_msleep(&dsi_ctx, 22);
\treturn dsi_ctx.accum_err;'''
new='''\tmipi_dsi_dcs_set_display_off_multi(&dsi_ctx);
\t/* Shutdown must progress to unprepare, including after a DCS timeout. */
\tmsleep(22);
\tif (dsi_ctx.accum_err)
\t\tdev_warn(&ctx->dsi->dev, "Display-off failed: %d; forcing teardown\\n",
\t\t\t dsi_ctx.accum_err);
\treturn 0;'''
assert s.count(old)==1; s=s.replace(old,new)
old='''\tmipi_dsi_dcs_enter_sleep_mode_multi(&dsi_ctx);
\tmipi_dsi_msleep(&dsi_ctx, 120);
\tsofef03f_power_off(ctx);
\treturn dsi_ctx.accum_err;'''
new='''\tmipi_dsi_dcs_enter_sleep_mode_multi(&dsi_ctx);
\t/* Preserve the stock wait even if the command bus is unresponsive. */
\tmsleep(120);
\tsofef03f_power_off(ctx);
\tif (dsi_ctx.accum_err)
\t\tdev_warn(&ctx->dsi->dev, "Sleep failed: %d; panel reset and power removed\\n",
\t\t\t dsi_ctx.accum_err);
\t/* Reset and VCI/VDDD are off: DRM must allow the next prepare/enable. */
\treturn 0;'''
assert s.count(old)==1; s=s.replace(old,new)
path.write_text(s)
(out/'panel-before.c').write_text(original)
(out/'panel-after.c').write_text(s)
diff=subprocess.run(['diff','-u','--label','a/drivers/gpu/drm/panel/panel-samsung-sofef03f.c','--label','b/drivers/gpu/drm/panel/panel-samsung-sofef03f.c',str(out/'panel-before.c'),str(path)],capture_output=True,text=True)
assert diff.returncode==1
(ref/'panel-shutdown-state.patch').write_text(diff.stdout)

# Reuse the verified PID 1 identity/mount checks with the current initramfs.
shutil.copyfile(out.parent/'rootfs01/samurai-rootfs',init/'usr/sbin/samurai-rootfs')
(init/'usr/sbin/samurai-rootfs').chmod(0o755)
p=init/'init'; text=p.read_text()
needle='# SAMURAI_USB_NCM_SSH: independent of the EUD console and F1 path.'
assert text.count(needle)==1 and 'SAMURAI_F2FS_ROOTFS' not in text
text=text.replace(needle,'''# SAMURAI_F2FS_ROOTFS: verified persistent userspace or diagnostic fallback.
. /usr/sbin/samurai-rootfs || echo "[rootfs] retaining diagnostic initramfs"

'''+needle)
p.write_text(text)

# The current firmware and same-handset read-only/COW services survive switch_root.
subprocess.run(['cp','-a',str(init/'lib/firmware')+'/.',str(root/'lib/firmware')],check=True)
subprocess.run(['cp','-a',str(init/'lib/modules')+'/.',str(root/'lib/modules')],check=True)
for p in (init/'usr/sbin').iterdir():
    if p.is_file() and (p.name.startswith('samurai-') or p.name=='qrtr-lookup'):
        shutil.copy2(p,root/'usr/sbin'/p.name)
subprocess.run(['cp','-a',str(init/'etc/samurai-wifi'),str(root/'etc')],check=True)
def write(name,text,mode=0o644):
    p=root/name.lstrip('/'); p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text);p.chmod(mode)
write('/etc/init.d/samurai-radio','''#!/sbin/openrc-run
description="Same-handset modem/Wi-Fi firmware and RAM COW services"
depend() {
    need localmount
    after udev
}
start() {
    ebegin "Starting Samurai modem and Wi-Fi"
    mkdir -p /run/samurai-wifi
    : > /run/samurai-wifi/boot-started
    ( /usr/sbin/samurai-wifi start > /run/samurai-wifi-boot.log 2>&1
      result=$?
      echo "$result" > /run/samurai-wifi/boot-finished.tmp
      mv /run/samurai-wifi/boot-finished.tmp /run/samurai-wifi/boot-finished
      echo "[wifi] startup exit=$result; see /run/samurai-wifi-boot.log" > /dev/kmsg
    ) < /dev/null > /dev/null 2>&1 &
    eend 0
}
''',0o755)
(root/'etc/runlevels/default/samurai-radio').symlink_to('/etc/init.d/samurai-radio')
# One Wi-Fi owner; NM will be introduced with the desktop after baseline validation.
for level in ['default','boot','sysinit']:
    for name in ['wpa_supplicant','networkmanager','routewrangler','nftables','swapfile']:
        p=root/'etc/runlevels'/level/name
        if p.is_symlink():p.unlink()
write('/etc/NetworkManager/conf.d/90-samurai-usb.conf','[keyfile]\nunmanaged-devices=interface-name:usb0;interface-name:wlan0\n')
write('/etc/samurai-rootfs-stage','kernel109\n')
subprocess.run(['bash','-n',str(init/'init'),str(init/'usr/sbin/samurai-rootfs'),str(root/'etc/init.d/samurai-radio')],check=True)
subprocess.run(['scripts/config','--enable','F2FS_FS','--enable','F2FS_FS_XATTR','--enable','F2FS_FS_POSIX_ACL','--enable','F2FS_FS_SECURITY','--set-str','INITRAMFS_SOURCE',str(init)],cwd=k,check=True)
print('CURRENT_KERNEL109_PANEL_FIX_F2FS_HANDOFF_AND_PERSISTENT_RADIO_SERVICES_CONFIGURED')
