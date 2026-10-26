from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel430/build-intree.py').read_text().replace('stage=430','stage=434').replace('camss_ds4_capture_candidate=True,','camss_ds4_capture_candidate=True,gtm_reopen_candidate=True,')
exec(compile(source,str(HERE/'build-intree.py'),'exec'))
