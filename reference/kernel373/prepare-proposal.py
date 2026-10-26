from pathlib import Path
import difflib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE.parent/'kernel372/shared-failure-validation.json').read_text())['passed']
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';relative='drivers/media/platform/qcom/camss/camss-icp-a5-boot.c';parent=json.loads((HERE.parent/'kernel372/source-state.json').read_text())['commit']
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
assert git('rev-parse','HEAD')==parent and not git('status','--porcelain')
before=(source/relative).read_text();s=before
a=s.index('\twritel(SHARED_IOVA, base + A5_QTABLE_PTR);',s.index('int camss_a5_start('));b=s.index('\n\tdma_wmb();',a)
program=s[a:b];s=s[:a]+s[b:]
helper='''static int program_hfi_parameters(struct camss_a5 *a5)
{
\tvoid __iomem *base = a5->resources.sierra;
\tstatic const u32 fields[][2] = {
\t\t{ A5_QTABLE_PTR, SHARED_IOVA },
\t\t{ A5_SFR_PTR, SHARED_IOVA + SFR_OFFSET },
\t\t{ A5_SHARED_PTR, SHARED_IOVA },
\t\t{ A5_SHARED_SIZE, SHARED_WINDOW },
\t\t{ A5_HEAP_PTR, HEAP_IOVA },
\t\t{ A5_HEAP_SIZE, HEAP_BYTES },
\t\t{ A5_QDSS_PTR, 0 },
\t\t{ A5_QDSS_SIZE, 0 },
\t\t{ A5_IO_PTR, IO_IOVA },
\t\t{ A5_IO_SIZE, IO_BYTES },
\t};
\tunsigned int i;
\tu32 value;

\tfor (i = 0; i < ARRAY_SIZE(fields); i++)
\t\twritel(fields[i][1], base + fields[i][0]);
\tfor (i = 0; i < ARRAY_SIZE(fields); i++) {
\t\tvalue = readl(base + fields[i][0]);
\t\tif (value != fields[i][1]) {
\t\t\tdev_err(a5->dev, "A5 HFI register %x readback %x expected %x\\n",
\t\t\t\tfields[i][0], value, fields[i][1]);
\t\t\treturn -EIO;
\t\t}
\t}
\treturn 0;
}

'''
anchor='int camss_a5_start(struct camss_a5 *a5, const struct firmware *firmware)';assert s.count(anchor)==1;s=s.replace(anchor,helper+anchor)
anchor='''\twritel(0x10, base + A5_RESET);
\twritel(A5_ENABLE | A5_WAKE | A5_WFI_GATE, base + A5_CONTROL);
\twritel(1, base + A5_INIT_REQUEST);
\tspin_unlock_irqrestore(&a5->control_lock, flags);'''
new='''\twritel(0x10, base + A5_RESET);
\t/* Match the OEM cold-boot sequence: CPU reset precedes HFI parameter
\t * programming. Never request initialization with unverified pointers.
\t */
\twritel(A5_ENABLE | A5_WAKE | A5_WFI_GATE, base + A5_CONTROL);
\tret = program_hfi_parameters(a5);
\tif (!ret)
\t\twritel(1, base + A5_INIT_REQUEST);
\tspin_unlock_irqrestore(&a5->control_lock, flags);
\tif (ret) {
\t\thrtimer_cancel(&a5->boot_timer);
\t\tgoto fail;
\t}
\tdev_info(a5->dev, "A5 HFI parameters verified after CPU reset\\n");'''
assert s.count(anchor)==1;s=s.replace(anchor,new)
(P/'boot-before.c').write_text(before);(P/'boot-proposed.c').write_text(s)
(HERE/'hfi-reset-order.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),s.splitlines(True),fromfile='a/'+relative,tofile='b/'+relative)))
(HERE/'proposal-state.json').write_text(json.dumps(dict(stage=373,parent=parent,source=str(source),relative=relative,applied=False,installed=False,firmware_cpu_started=False),indent=2)+'\n')
print('Prepared post-CPU-reset HFI programming and mandatory readback; not applied or launched.')
