from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel363/camera-check.py').read_text().replace('/var/lib/samurai/k363-camera-check-','/var/lib/samurai/k365-camera-check-').replace("'stage':363","'stage':365")
s=s.replace("else 'r2'","else 'r1'").replace("tar.add(host.PRIVATE/'pipeline-fixture'", "tar.add(host.PRIVATE.parent/'kernel363/pipeline-fixture'")
(HERE/'camera-check.py').write_text(s)
s=(HERE.parent/'kernel363/camera-check-body.py').read_text().replace('/var/lib/samurai/k363-work/boot-id-private.txt','/var/lib/samurai/k365-work/boot-id-private.txt').replace('stage=363','stage=365')
s=s.replace('new_kernel_image_exercised=True','kernel_image_stage=363,dt_stage=365,static_board_dt_exercised=True')
(HERE/'camera-check-body.py').write_text(s)
for name in ['camera-check.py','camera-check-body.py']:compile((HERE/name).read_text(),name,'exec')
print('Prepared DT365 camera check; reuse verified fixture363 and installed362 binaries.')
