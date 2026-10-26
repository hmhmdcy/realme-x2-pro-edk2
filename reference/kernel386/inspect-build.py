from pathlib import Path
import importlib.util,json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage)
build=storage.mounted_build();source=build.parent/'source354'
lines=(build/'Module.symvers').read_text().splitlines()
rows=[l for l in lines if any(n in l for n in ['vb2_vmalloc_memops','vb2_queue_init','vb2_buffer_done','vb2_queue_release'])]
(P/'Makefile.modpost-private').write_text((source/'scripts/Makefile.modpost').read_text())
files=[str(p.relative_to(build)) for p in (build/'drivers/media/common/videobuf2').glob('*symvers')]
print(json.dumps(dict(symvers_lines=len(lines),relevant_exports=rows,per_directory_symvers=files,modversions=[l for l in (build/'.config').read_text().splitlines() if 'CONFIG_MODVERSIONS' in l]),indent=2))
