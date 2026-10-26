from pathlib import Path
import shutil
import host
HERE=Path(__file__).resolve().parent
shutil.copyfile(host.PRIVATE.parent/'kernel437/factory-s5kgw1-private.yaml',host.PRIVATE/'factory-s5kgw1-private.yaml')
source=(HERE.parent/'kernel435/check-ipa.py').read_text().replace('stage=435','stage=439').replace('camss435-contract','camss439-regression')
source=source.replace("(HERE/'gtm-contract-body.cpp')","(HERE.parent/'kernel435/gtm-contract-body.cpp')").replace("HERE/'profile-contract.cpp'","HERE.parent/'kernel435/profile-contract.cpp'")
source=source.replace("T+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so.p/gamma_profile.cpp.o',", "T+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so.p/gamma_profile.cpp.o',T+'/output/src/ipa/camss-vfe/ipa_camss_vfe.so.p/colour_correction_profile.cpp.o',")
exec(compile(source,str(HERE/'check-regressions.py'),'exec'))
