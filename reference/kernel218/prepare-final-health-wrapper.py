from pathlib import Path

here=Path(__file__).resolve().parent
lines=(here.parent/'kernel217/final-health.py').read_text().splitlines()
old=[line for line in lines if line.startswith('assert json.loads') and 'factory-mode-candidate-build-validation.json' in line]
assert len(old)==1
text='\n'.join(lines)+'\n'
text=text.replace(old[0],"assert json.loads((here/'cpu-isp-tests-validation.json').read_text())['real_libcamera_cpu_isp_and_dma_heap_test']")
text=text.replace('k217-','k218-').replace('stage=217,','stage=218,').replace('native-final-health217','native-final-health218')
path=here/'final-health.py';assert not path.exists();path.write_text(text)
compile(text,str(path),'exec')
print('Fresh218 final health wrapper prepared; not executed')
