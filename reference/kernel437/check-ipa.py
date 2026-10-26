from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel435/check-ipa.py').read_text().replace('stage=435','stage=437').replace('camss435-contract','camss437-regression')
source=source.replace("(HERE/'gtm-contract-body.cpp')","(HERE.parent/'kernel435/gtm-contract-body.cpp')")
source=source.replace("HERE/'profile-contract.cpp'","HERE.parent/'kernel435/profile-contract.cpp'")
exec(compile(source,str(HERE/'check-ipa.py'),'exec'))
