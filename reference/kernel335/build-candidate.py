from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel321/build-candidate.py').read_text().replace('libcamera321-lsc-built','libcamera335-ccm-built').replace('libcamera-before321','libcamera-before335').replace('stage=321','stage=335')
s=s.replace("'src/ipa/camss-vfe/ipa_camss_vfe.so.sign'","'src/ipa/camss-vfe/ipa_camss_vfe.so.sign','src/libcamera/libcamera.so.0.7.2'")
exec(compile(s,str(HERE/'build-candidate.py'),'exec'),dict(__file__=str(HERE/'build-candidate.py'),__name__='__main__'))
