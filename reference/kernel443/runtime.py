from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel442/runtime.py').read_text()
source=source.replace("exec(compile(source,str(HERE/'runtime.py'),'exec'))", "source=source.replace('k442-callback-timing-','k443-gst-consumer-')\nexec(compile(source,str(HERE/'runtime.py'),'exec'))")
exec(compile(source,str(HERE/'runtime.py'),'exec'))
