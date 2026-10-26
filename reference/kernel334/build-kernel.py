from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel318/build-kernel.py').read_text().replace('kernel318','kernel334').replace('camera318-lsc-kernel','camera334-ccm-kernel').replace('qcom-camss-lsc318','qcom-camss-ccm334').replace('stage=318','stage=334')
exec(compile(s,str(HERE/'build-kernel.py'),'exec'),dict(__file__=str(HERE/'build-kernel.py'),__name__='__main__'))
