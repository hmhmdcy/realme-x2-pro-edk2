from pathlib import Path
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel103')
s=(ref/'collect-checkpoint.sh').read_text().replace('k103-checkpoint','k103-checkpoint-retry1')
s=s.replace(' /lib/modules/*/extra/*.ko > "$dir/deployment.sha"',' > "$dir/deployment.sha"\nfind /lib/modules -type f -name "*.ko" -exec sha256sum \'{}\' \';\' >> "$dir/deployment.sha"')
s=s.replace('cp -a /tmp/k103-audio-runtime "$dir/first-runtime-partial"', 'cp -a /tmp/k103-audio-runtime "$dir/first-runtime-partial"\ncp -a /tmp/k103-checkpoint "$dir/first-checkpoint-partial"')
assert not (ref/'collect-checkpoint-retry1.sh').exists()
(ref/'collect-checkpoint-retry1.sh').write_text(s)
print('MODULE_PATH_ASSUMPTION_REMOVED; FIRST_CHECKPOINT_RETAINED')
