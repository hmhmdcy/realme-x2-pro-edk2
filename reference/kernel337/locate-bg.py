from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel320/locate-stock-lsc.py').read_text().replace("P=Path('/mnt/e/edk2-samurai-out/kernel320')","P=Path('/mnt/e/edk2-samurai-out/kernel337')")
s=s.replace("path=P.parent/'kernel316/hal-source/camera.qcom.so'","path=P.parent/'kernel328/stats-source/com.qti.stats.aec.so'")
s=s.replace("[b'FormatLSCData',b'FormatDataTypeByte',b'meshHWRollOffSize out of bound',b'Memory allocation for LSC failed']","[b'ProcessBGStats',b'CalculateLumaWeight',b'ProcessBGStatsRegion']")
s=s.replace('stock-lsc-','stock-bg-')
exec(compile(s,str(HERE/'locate-bg.py'),'exec'),dict(__file__=str(HERE/'locate-bg.py')))
