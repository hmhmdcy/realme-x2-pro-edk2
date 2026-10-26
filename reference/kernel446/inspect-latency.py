from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel443/inspect-latency.py').read_text().replace('stage=443','stage=446')
source=source.replace("for folder in sorted(root.glob('*-native'))+sorted(root.glob('*-isolated')):","for folder in [root/'1280x720-isolated',root/'1920x1080-isolated']:")
exec(compile(source,str(HERE/'inspect-latency.py'),'exec'))
