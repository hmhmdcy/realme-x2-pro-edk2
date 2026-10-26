from pathlib import Path
import json
here=Path(__file__).resolve().parent
text=(here.parent/'kernel223/build-r8-candidate.py').read_text()
text=text.replace('kernel223','kernel224').replace('libcamera214-before223','libcamera214-before224').replace('libcamera223','libcamera224').replace('packages223','packages224').replace('packages-config223','packages-config224').replace('samurai-camera-config223','samurai-camera-config224')
text=text.replace("cache=root/'work/libcamera220-built'","cache=root/'work/libcamera223-built'")
text=text.replace('r8','r9').replace('r7','r8').replace('r3','r4').replace('prior13','prior14').replace('stage=223','stage=224').replace('0014-simple-capture-control-snapshot.patch','0015-simple-raw-only-statistics.patch')
compile(text,'full-r9-build224','exec');(here/'build-r9-candidate.py').write_text(text)
code=(here.parent/'kernel223/run-baseline-raw-gap.py').read_text()
a=code.index('code="from pathlib import Path');b=code.index("code=(here.parent/'kernel219/native-mode-runner.py')",a)
code=code[:a]+code[b:]
code=code.replace("proof=json.loads((here/'paired-probe-build-validation.json').read_text());data=(host.PRIVATE/'paired-frame-probe').read_bytes();assert hashlib.sha256(data).hexdigest()==proof['binary_sha256']",'')
code=code.replace('k223-baseline','k224-baseline').replace("'k223-capture-'","'k224-capture-'").replace('stage=223','stage=224')
code=code.replace("tag='baseline-raw-gap'","tag='r8-baseline-raw-statistics'")
code += "\nassert all(f['exposure_us']==-1 and f['gain']==-1 for f in r['frames'])\n"
compile(code,'raw-baseline224','exec');(here/'run-baseline-raw-gap.py').write_text(code)
print('K224_BUILD_AND_RAW_BASELINE_PREPARED')
