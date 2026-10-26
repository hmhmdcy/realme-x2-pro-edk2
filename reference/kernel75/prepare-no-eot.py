from pathlib import Path
import difflib,hashlib

root=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel75')
out=Path('/mnt/e/edk2-samurai-out/kernel75')
kernel=Path('/home/cy122/x2pro-linux/linux')
relative='drivers/gpu/drm/panel/panel-samsung-sofef03f.c'
p=kernel/relative
before=p.read_text()
assert hashlib.sha256(p.read_bytes()).hexdigest()=='6501e48e6658b94ee1ef9b2b8e9fc0af5f9c73faa4afad9e0a931eea46256da3'
backup=out/'panel-samsung-sofef03f.c.before'
assert not backup.exists()
needle='dsi->mode_flags = MIPI_DSI_MODE_LPM | MIPI_DSI_MODE_DSC_ALL_SLICES_IN_PKT;'
assert before.count(needle)==1
after=before.replace(needle,'''/* Stock host config has append_tx_eot disabled. */
	dsi->mode_flags = MIPI_DSI_MODE_LPM | MIPI_DSI_MODE_NO_EOT_PACKET |
			  MIPI_DSI_MODE_DSC_ALL_SLICES_IN_PKT;''')
backup.write_text(before)
p.write_text(after)
(root/'panel-no-eot.patch').write_text('diff --git a/'+relative+' b/'+relative+'\n'+''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),'a/'+relative,'b/'+relative)))
(root/'build-no-eot.sh').write_text((root/'build-matched.sh').read_text().replace('matched','no-eot'))
(root/'prepare-no-eot-flash.py').write_text((root/'prepare-dsc-diag-flash.py').read_text().replace('dsc-diag','no-eot'))
print('Changed only the panel EOT mode flag, matching stock append_tx_eot=false')
