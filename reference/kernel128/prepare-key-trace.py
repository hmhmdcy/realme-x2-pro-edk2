from pathlib import Path
r=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel128')
s=(r/'test-5ghz-once.sh').read_text().replace('k128-wifi-5ghz-once','k128-wifi-keytrace-baseline').replace('for sample in 0 1 2 3 4 5 6 7 8 9; do','for sample in 0 1 2; do').replace('if test "$sample" != 9; then sleep 5; fi','if test "$sample" != 2; then sleep 2; fi')
(r/'test-keytrace-inner.sh').write_text(s)
print('K128_FRESH_KEYTRACE_INNER_BOUNDED_TEST_READY')
