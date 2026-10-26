from pathlib import Path

here=Path(__file__).resolve().parent
text=(here.parent/'kernel217/build-factory-mode-candidate.py').read_text()
text=text.replace("kernel217'","kernel219'")
text=text.replace("assert json.loads((here/'factory-mode-crosscheck-validation.json').read_text())['mode_register_records_verified']==174\n",'')
# Original build consumes the already independently decoded private mode data.
text=text.replace("private/'factory-imx471-modes-private.json'","private.parent/'kernel217/factory-imx471-modes-private.json'")
text=text.replace("backup=private/'candidate-build-before'","backup=private/'candidate-build-before'")
needle="files|={kernel/name for name in ['.config','Module.symvers','modules.order']}"
assert text.count(needle)==1
text=text.replace(needle,"cci_directory=kernel/'drivers/media/v4l2-core'\nfiles|={p for pattern in ['v4l2-cci*','.v4l2-cci*'] for p in cci_directory.glob(pattern) if p.is_file()}\n"+needle)
text=text.replace("'-j3','drivers/media/i2c/imx471.ko'","'-j3','drivers/media/v4l2-core/v4l2-cci.ko','drivers/media/i2c/imx471.ko'")
text=text.replace('    for path in current_files:',"    current_files|={p for pattern in ['v4l2-cci*','.v4l2-cci*'] for p in cci_directory.glob(pattern) if p.is_file()}\n    for path in current_files:")
text=text.replace("assert path.parent==source.parent and (path.name.startswith('imx471') or path.name.startswith('.imx471'));path.unlink()","assert path.parent in [source.parent,cci_directory] and path.name.startswith(('imx471','.imx471','v4l2-cci','.v4l2-cci'));path.unlink()")
text=text.replace('stage=217,','stage=219,')
exec(compile(text,'isolated-mode-driver-build219','exec'))
