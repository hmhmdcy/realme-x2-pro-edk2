from pathlib import Path
import ast

here=Path(__file__).resolve().parent
source=(here.parent.parent/'kernel206/final-health.py').read_text()
source=source.replace('k205r2-runtime','k207r2-runtime').replace('k206','k207r2').replace('stage=206','stage=207')
source=source.replace('d0906a5abb939fa5d1e906692b0ac769f0760857d4a9780a07ad5b59d1c4ca4e','b3bb82b9d090a5d06e9ba2ca24e3373ab1c1e7cc2a5c6b603e2acb02715487a1')
source=source.replace('ffb65d31b337fbdad89ff9c575b133574756121f75cd2967da10f1028c1b5fbd','854c9a8c787d68ccefc998064983f3aa67141fe94def27f4dde87925bd18f24f')
source=source.replace('same205_r2_boot_verified=True, rebooted=False','same_second207_boot_verified=True, rebooted_during_health_check=False')
source=source.replace('tftp_bootstrap_mcfg_requests_not_yet_retested=True','tftp_bootstrap_mcfg_requests_retested=True,stock_mcfg_auto_staging_verified=True,existing_ntp_sources_manually_refreshed=True')
marker="remoteprocs = {(p / 'name')"
extra="""assert sha('/usr/sbin/samurai-modem-configs')=='d4c62be6054b3ff74f3ed2868c4b456ccb519f75954ad7094235826559a64862'
manifest=json.loads(Path('/run/samurai-wifi/mcfg-state/source-manifest-private.json').read_text())
assert len(manifest)==173 and manifest==json.loads((root/'k207-stock-mcfg-inventory/mcfg-source-manifest-private.json').read_text())
fwroot=Path('/run/samurai-wifi/firmware/qcom/sm8150/realme/samurai')
assert all(sha(fwroot/name)==item['sha256'] for name,item in manifest.items())
assert all(not p.name.startswith('samurai-validation') for p in Path('/run/samurai-wifi/tftp-rw').iterdir())
"""
source=source.replace(marker,extra+marker)
ast.parse(source)
(here/'final-health.py').write_text(source)
print('Final health source prepared; no device operation.')
