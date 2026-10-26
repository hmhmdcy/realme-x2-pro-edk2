"""Keep original cold restore while authenticating this path-only operator."""
from pathlib import Path
import importlib.util,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def load(path,name):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def binder():
    folder=HERE.parent/'irq-native-usb-pm-rollback-host-candidate'
    m=load(folder/'bind.py','pm_path_current_rollback_binder')
    def reviewed(profile,stage,fetched,context=None):
        m.source_check();saved=load(folder/'saved-proof.py','pm_path_saved_restore_actions')
        saved.OPERATOR_PATH=HERE/'fastboot-operator.py'
        return saved.review_profile_sources(profile,stage,fetched,context)
    m.review_sources=reviewed
    return m

def owner():
    m=load(HERE.parent/'irq-native-usb-pm-rollback-connected-candidate/host.py','pm_original_cold_restore_owner')
    original=m.load_module;expected=(HERE.parent/'irq-native-usb-pm-rollback-host-candidate/bind.py').resolve()
    def module(path,name):
        return binder() if m.local(path).resolve()==expected else original(path,name)
    m.load_module=module
    return m

def recovery_sources(sources):
    original=sources.load
    def selected(name):
        if name=='rollback_host':return owner()
        if name=='rollback_binder':return binder()
        return original(name)
    sources.load=selected
    return sources

if __name__=='__main__':raise SystemExit(owner().main())
