from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel374/collect-recovery.py').read_text().replace('stage=374','stage=377').replace('k374-boot-','k377-boot-').replace('k373-recovered','k374-recovered')
(HERE/'collect-recovery.py').write_text(s)
s=(HERE.parent/'kernel375/adopt-recovered-boot.py').read_text().replace('stage=375','stage=377').replace('k375-boot-','k377-boot-').replace("directory=Path('/var/lib/samurai/k375-recovered')", "directory=Path('/var/lib/samurai/k377-recovered')")
(HERE/'adopt-recovered-boot.py').write_text(s)
print('Prepared read-only recovery inventory and matching temporary firmware cleanup on a verified new boot.')
