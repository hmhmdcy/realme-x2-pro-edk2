"""Original logdump owner with the already-reviewed WSL stage-path correction."""
from pathlib import Path
import importlib.util,inspect,sys
sys.dont_write_bytecode=True
if sys.flags.optimize:raise RuntimeError('nonoptimized Python required')
HERE=Path(__file__).resolve().parent
_OWNER=None

def owner():
    global _OWNER
    if _OWNER is None:
        path=HERE.parent/'irq-native-usb-pm-retained-source-candidate/reviewer.py'
        spec=importlib.util.spec_from_file_location('pm_fastboot_path_review',path);review=importlib.util.module_from_spec(spec);spec.loader.exec_module(review)
        pins=review.source_check()
        module=review.load(pins['operator']['path'],'pm_original_fastboot_owner') if 'operator' in pins else review.load(HERE.parent/'irq-native-usb-pm-activation-device-candidate/fastboot-operator.py','pm_original_fastboot_owner')
        source=inspect.getsource(module.validate_context)
        old="""    import importlib.util
    spec=importlib.util.spec_from_file_location('current_irq_stage_review',HERE/'stage-proof.py')
    proof=importlib.util.module_from_spec(spec);spec.loader.exec_module(proof)"""
        module.require(source.count(old)==1,'exact original context source shape')
        module.path_correct_stage=review.current_stage_module
        exec(compile(source.replace(old,'    proof=path_correct_stage()'),'<current-path-correct-context>','exec'),module.__dict__)
        module.__file__=str(Path(__file__).resolve())
        _OWNER=module
    return _OWNER

if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--_worker':owner().worker(sys.argv[2])
    else:raise SystemExit(owner().main())
