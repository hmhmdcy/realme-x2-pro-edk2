from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel443/inspect-latency.py').read_text().replace('stage=443','stage=448')
source=source.replace("for folder in sorted(root.glob('*-native'))+sorted(root.glob('*-isolated')):","for folder in [root/(f'{w}x{h}-'+k) for w,h in [(1280,720),(1920,1080)] for k in ['native','isolated']]:")
exec(compile(source,str(HERE/'inspect-latency.py'),'exec'))
