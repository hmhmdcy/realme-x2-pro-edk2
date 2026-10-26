from pathlib import Path
ref=Path(__file__).resolve().parent;old=ref.parent/'kernel197'
for name in ['baseline.py','collect-front-before.py','inspect-live-resources.py','run-native.py']:(ref/name).write_text((old/name).read_text().replace('k197','k198').replace('stage=197','stage=198'))
print('Fresh baseline scripts prepared')
