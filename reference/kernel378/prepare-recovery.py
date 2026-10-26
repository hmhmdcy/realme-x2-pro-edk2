from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel377/collect-recovery.py').read_text().replace('stage=377','stage=378').replace('k377-boot-','k378-boot-').replace('k374-recovered','k377-recovered')
(HERE/'collect-recovery.py').write_text(s)
s=(HERE.parent/'kernel377/adopt-recovered-boot.py').read_text().replace('stage=377','stage=378').replace('k377-boot-','k378-boot-').replace('k374-recovered','k377-recovered').replace("directory=Path('/var/lib/samurai/k377-recovered')", "directory=Path('/var/lib/samurai/k378-recovered')")
(HERE/'adopt-recovered-boot.py').write_text(s)
print('Prepared new-boot inventory and hash-checked temporary firmware cleanup.')
