from pathlib import Path
import ast
import hashlib
import json
import shutil
import tarfile

ref = Path(__file__).resolve().parent
out = Path('E:/edk2-samurai-out/kernel180')
archive = out / 'k180-dmic0-ucm180-low24-private.tar.gz'
with tarfile.open(archive) as capture, tarfile.open(out / 'k180-runtime-private.tar.gz') as runtime:
    capture_boot = capture.extractfile('k180-dmic0-ucm180-low24/boot-id-private.txt').read()
    runtime_boot = runtime.extractfile('k180-runtime/boot-id-private.txt').read()
    first_boot = json.loads(runtime.extractfile('k180-runtime/validation.json').read())
    raw = json.loads(capture.extractfile('k180-dmic0-ucm180-low24/capture-validation.json').read())
assert capture_boot == runtime_boot and first_boot['kernel_build'] == 180
assert first_boot['kernel_version'].startswith('#180 ') and raw['kernel_build'] == 176
def function_ast(path):
    return ast.dump(next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == 'analyze_samples'))
assert function_ast(ref/'analyze-acoustic.py') == function_ast(ref.parent/'kernel178/analyze-acoustic.py')
old = out / 'dmic0-ucm180-low24-analysis.json'
saved = out / 'dmic0-ucm180-low24-analysis-before-label-fix-private.json'
assert not saved.exists()
shutil.copyfile(old, saved)
for name in ['capture-acoustic.py', 'test-desktop-duplex.py', 'analyze-desktop.py']:
    path = ref / name
    path.write_text(path.read_text().replace('kernel_build=176', 'kernel_build=180'))
path = ref/'analyze-acoustic.py'
source = path.read_text().replace('kernel_build=176', 'kernel_build=180')
source = source.replace("summary=dict(stage=180,kernel_build=180,", "summary=dict(stage=180,kernel_build=180,original_capture_report_kernel_build=report['kernel_build'],capture_boot_matched_verified_runtime180=True,")
path.write_text(source)
note = dict(stage=180,original_capture_report_kernel_build=176,verified_kernel_build=180,
            capture_boot_matches_verified_runtime180=True,executed_capture_uname_guard='#180 ',
            raw_capture_archive_preserved=True,raw_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
            numerical_analysis_function_unchanged=True,correction_applies_to_derived_metadata_only=True)
(ref/'capture-metadata-correction.json').write_text(json.dumps(note,indent=2)+'\n')
print('K180_CAPTURE_BOOT_MATCHED_METADATA_CORRECTION_RECORDED')
