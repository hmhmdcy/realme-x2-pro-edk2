from pathlib import Path
ref=Path(__file__).resolve().parent;s=(ref.parent/'kernel193/export-native.py').read_text().replace('k193-','k194-').replace('stage=193','stage=194');(ref/'export-native.py').write_text(s)
print('Stage194 native exporter prepared')
