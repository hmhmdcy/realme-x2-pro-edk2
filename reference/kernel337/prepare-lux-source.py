from pathlib import Path
HERE=Path(__file__).resolve().parent
for name in ['aec_lux.h','aec_lux.cpp']:
 source=(HERE.parent/'kernel336/libipa'/name).read_text()
 if name.endswith('.cpp'):source=source.replace('cell<0 || cell>255','cell<0')
 else:source=source.replace('8-bit lux-luma','8-bit-scaled lux-luma (not capped after colour compensation)')
 (HERE/'libipa'/name).write_text(source)
print('Retained336 lux math and removed the artificial post-compensation255 cap.')
