"""Include the in-tree CCI symbol provider and preserve its build artifacts too."""
from pathlib import Path
here=Path(__file__).resolve().parent
source=(here/'build-factory-mode-candidate.py').read_text()
source=source.replace("out=private/'candidate-build'","out=private/'candidate-build-r2'").replace("backup=private/'candidate-build-before'","backup=private/'candidate-build-r2-before'")
needle="files|={kernel/name for name in ['.config','Module.symvers','modules.order']}"
assert needle in source
source=source.replace(needle,"cci_directory=kernel/'drivers/media/v4l2-core'\nfiles|={p for pattern in ['v4l2-cci*','.v4l2-cci*'] for p in cci_directory.glob(pattern) if p.is_file()}\n"+needle)
source=source.replace("'-j3','drivers/media/i2c/imx471.ko'","'-j3','drivers/media/v4l2-core/v4l2-cci.ko','drivers/media/i2c/imx471.ko'")
needle="    for path in current_files:"
assert needle in source
source=source.replace(needle,"    current_files|={p for pattern in ['v4l2-cci*','.v4l2-cci*'] for p in cci_directory.glob(pattern) if p.is_file()}\n"+needle)
source=source.replace("assert path.parent==source.parent and (path.name.startswith('imx471') or path.name.startswith('.imx471'));path.unlink()","assert path.parent in [source.parent,cci_directory] and path.name.startswith(('imx471','.imx471','v4l2-cci','.v4l2-cci'));path.unlink()")
exec(compile(source,'candidate-build-with-cci-provider-r2','exec'))
