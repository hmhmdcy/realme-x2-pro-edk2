from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel318/build-kernel.py').read_text().replace('kernel318','kernel338').replace('/home/cy122/x2pro-linux/camera318-lsc-kernel','/mnt/samurai-full282/source338').replace('qcom-camss-lsc318','qcom-camss-grid338').replace('stage=318','stage=338')
exec(compile(s,str(HERE/'build-kernel.py'),'exec'),dict(__file__=str(HERE/'build-kernel.py'),__name__='__main__'))
