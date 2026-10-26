from pathlib import Path
import importlib.util

here=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('fdt_compare219',here.parent/'kernel211/fdt_compare.py')
fdt=importlib.util.module_from_spec(spec);spec.loader.exec_module(fdt)
namespace=dict(__file__=str(here/'build-package.py'),fdt_compare_function=fdt.compare)
exec(compile((here/'build-package.py').read_text(),'boot-builder219','exec'),namespace)
