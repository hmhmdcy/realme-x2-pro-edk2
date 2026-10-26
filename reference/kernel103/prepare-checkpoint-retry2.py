from pathlib import Path
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel103')
s=(ref/'collect-checkpoint-retry1.sh').read_text().replace('k103-checkpoint-retry1','k103-checkpoint-retry2')
s=s.replace('find . -type f ! -name SHA256SUMS','find . -type f ! -path ./SHA256SUMS')
assert not (ref/'collect-checkpoint-retry2.sh').exists()
(ref/'collect-checkpoint-retry2.sh').write_text(s)
print('OUTER_MANIFEST_WILL_BIND_EVERY_NESTED_MANIFEST')
