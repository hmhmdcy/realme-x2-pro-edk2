from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel420/build-packages.py').read_text()
source=source.replace('r31/r26','r32/r27').replace('stage=420','stage=440').replace('420-r31','440-r32').replace('99990.7.2-r31','99990.7.2-r32').replace('0.1.0-r26','0.1.0-r27')
source=source.replace("['package-source-validation.json','ipa-contract-validation.json']", "['package-source-validation.json','patch-chain-validation.json']")
source=source.replace('440-r32','440-r32-r2').replace('report=dict(stage=440,','report=dict(stage=440,build_iteration=2,')
exec(compile(source,str(HERE/'build-packages.py'),'exec'))
