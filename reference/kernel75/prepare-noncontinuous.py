from pathlib import Path
import difflib,hashlib,json

root=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel75')
out=Path('/mnt/e/edk2-samurai-out/kernel75')
kernel=Path('/home/cy122/x2pro-linux/linux')
changes=[]
relative='drivers/gpu/drm/panel/panel-samsung-sofef03f.c'
p=kernel/relative
before=p.read_text()
needle='''/* Stock host config has append_tx_eot disabled. */
	dsi->mode_flags = MIPI_DSI_MODE_LPM | MIPI_DSI_MODE_NO_EOT_PACKET |
			  MIPI_DSI_MODE_DSC_ALL_SLICES_IN_PKT;'''
assert before.count(needle)==1
after=before.replace(needle,'''/* Stock host config disables EOT append and forced HS clock. */
	dsi->mode_flags = MIPI_DSI_MODE_LPM | MIPI_DSI_MODE_NO_EOT_PACKET |
			  MIPI_DSI_CLOCK_NON_CONTINUOUS |
			  MIPI_DSI_MODE_DSC_ALL_SLICES_IN_PKT;''')
assert not (out/'panel-samsung-sofef03f.c.no-eot-before').exists()
(out/'panel-samsung-sofef03f.c.no-eot-before').write_text(before)
changes.append((relative,before,after))

relative='drivers/gpu/drm/msm/dsi/dsi_host.c'
p=kernel/relative
before=p.read_text()
needle='''		dsi_write(msm_host, REG_DSI_LANE_CTRL,
			lane_ctrl | DSI_LANE_CTRL_CLKLN_HS_FORCE_REQUEST);
	}

	data |= DSI_CTRL_ENABLE;'''
assert before.count(needle)==1
after=before.replace(needle,'''		dsi_write(msm_host, REG_DSI_LANE_CTRL,
			lane_ctrl | DSI_LANE_CTRL_CLKLN_HS_FORCE_REQUEST);
	} else {
		/* Clear a continuous-clock request inherited from firmware. */
		msm_dsi_phy_set_continuous_clock(phy, false);
		lane_ctrl = dsi_read(msm_host, REG_DSI_LANE_CTRL);
		lane_ctrl &= ~DSI_LANE_CTRL_CLKLN_HS_FORCE_REQUEST;
		dsi_write(msm_host, REG_DSI_LANE_CTRL, lane_ctrl);
	}

	data |= DSI_CTRL_ENABLE;''')
assert not (out/'dsi_host.c.before').exists()
(out/'dsi_host.c.before').write_text(before)
changes.append((relative,before,after))

patch=''
for relative,before,after in changes:
    (kernel/relative).write_text(after)
    patch+='diff --git a/'+relative+' b/'+relative+'\n'+''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),'a/'+relative,'b/'+relative))
(root/'noncontinuous.patch').write_text(patch)
(root/'build-noncontinuous.sh').write_text((root/'build-matched.sh').read_text().replace('matched','noncontinuous'))
(root/'prepare-noncontinuous-flash.py').write_text((root/'prepare-dsc-diag-flash.py').read_text().replace('dsc-diag','noncontinuous'))
print('Matched stock noncontinuous clock; cleared inherited host/PHY forcing')
