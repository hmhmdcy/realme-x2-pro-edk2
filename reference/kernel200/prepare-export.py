from pathlib import Path
ref=Path(__file__).resolve().parent
s=(ref.parent/'kernel199/export-native.py').read_text().replace('k199','k200').replace('stage=199','stage=200').replace('k200-baseline/boot-id-private.txt','k200-runtime/boot-id-private.txt')
(ref/'export-native.py').write_text(s)
print('K200_PRIVATE_NATIVE_EXPORT_PREPARED')
