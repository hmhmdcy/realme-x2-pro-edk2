"""Lock the maintained tree, then keep candidates separate from it."""
from pathlib import Path
import hashlib,importlib.util,json,shutil
REF=Path(__file__).resolve().parent;PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel232');PRIVATE.mkdir(exist_ok=True)
KERNEL=Path('/home/cy122/pmos-samurai-kernel136/kernel')
sp=importlib.util.spec_from_file_location('p227',REF.parent/'kernel227/prepare-fastrpc.py');p=importlib.util.module_from_spec(sp);sp.loader.exec_module(p)
assert p.snapshot()==json.loads((PRIVATE.parent/'kernel228/canonical-after-private.json').read_text())
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
names=['drivers/mfd/qcom-pm8008.c','drivers/reset/Kconfig','drivers/reset/Makefile','Documentation/devicetree/bindings/mfd/qcom,pm8008.yaml','arch/arm64/boot/dts/qcom/sm8150-samurai.dts','.config','Module.symvers','modules.order']
before=PRIVATE/'originals';assert not before.exists();before.mkdir()
for name in names:
 path=before/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(KERNEL/name,path)
(PRIVATE/'kernel-before-private.json').write_text(json.dumps(p.snapshot(),indent=2)+'\n')
board=PRIVATE.parent/'kernel219/timing-source/sm8150-samurai.dts';assert board.is_file()
proof=json.loads((REF.parent/'kernel219/timing-candidate-source-validation.json').read_text());assert sha(board)==proof['board_sha256']
candidate=PRIVATE/'candidate';assert not candidate.exists();candidate.mkdir();shutil.copyfile(board,candidate/'sm8150-samurai.dts');shutil.copyfile(KERNEL/'drivers/mfd/qcom-pm8008.c',candidate/'qcom-pm8008.c')
(PRIVATE/'current-work-private.json').write_text(json.dumps(dict(stage=232,state='reset provider candidate written; maintained kernel and phone untouched; MFD/DT integration pending',guard='/var/lib/samurai/k230-runtime/boot-id-private.txt',full_peripheral_goal_active=True,active_native_session=None,active_build_session=None,transition_pending=False,front_known_colour_test_deferred_by_user=True,next='Implement PM8008 exclusive reset backend + persistent Q/P/provider links + P cleanup; candidate DTS based on actual219, no VIN guesses; build/test offline before device deployment'),indent=2)+'\n')
report=dict(stage=232,canonical_after228_preserved=True,original_sources_locked={name:sha(KERNEL/name) for name in names},board_source_matches_deployed219=True,phone_or_canonical_not_modified=True)
(REF/'baseline-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(stage=232,isolated_source_baseline_created=True,deployed219_board_source_verified=True,canonical_and_phone_untouched=True)))
