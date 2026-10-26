"""Compile standard-API k295 statistics and real-scene probes."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
s=(ROOT.parent/'kernel294/prepare-tools.py').read_text().split("s=(OLD/'native-wb-params.py')")[0]
s=s.replace('/kernel294','/kernel295').replace('stage=294','stage=295').replace('wrong-kernel-k294','wrong-kernel-k295')
exec(compile(s,'compile-probes.py','exec'),{'__file__':__file__})
print('Strict k295 stats and optical probes compiled; self-tests and wrong-kernel guards passed.')
