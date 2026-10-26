from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel321/build-candidate.py').read_text().replace('libcamera321-lsc-built','libcamera330-wb-built').replace('libcamera-before321','libcamera-before330').replace('stage=321','stage=330')
s=s.replace("'-j4','src/ipa/camss-vfe/ipa_camss_vfe.so.sign'", "'-j4','src/libcamera/libcamera.so.0.7.2','src/ipa/camss-vfe/ipa_camss_vfe.so.sign'")
exec(compile(s,str(HERE/'build-candidate.py'),'exec'),dict(__file__=str(HERE/'build-candidate.py'),__name__='__main__'))
