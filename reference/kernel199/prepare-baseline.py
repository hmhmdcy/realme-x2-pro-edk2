from pathlib import Path
ref=Path(__file__).resolve().parent;old=ref.parent/'kernel198'
for name in ['baseline.py','collect-front-before.py','inspect-live-resources.py','run-native.py']:(ref/name).write_text((old/name).read_text().replace('k198','k199').replace('stage=198','stage=199'))
print('Fresh baseline scripts prepared')
