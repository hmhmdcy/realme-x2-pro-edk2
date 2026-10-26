from pathlib import Path
import json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
d=json.loads((HERE/'stock-lsc-layout-validation.json').read_text())
assert d['new_layout_zero_samples']==0 and d['independent_sequential_c_decoder'] and d['both_retained_reads_match']
d.update(skipped_bytes_all_ff=True,raw_values_repaired=False,unique_factory_golden_tables=2,unique_factory_core_tables=17)
(HERE/'stock-lsc-layout-validation.json').write_text(json.dumps(d,indent=2)+'\n')
p=ROOT/'linux-port/camera/deployment-lock.json';d=json.loads(p.read_text())
d.update(in_progress_stage=320,in_progress_evidence='../../reference/kernel320/README.md',in_progress_installed=False,
 lsc_unit_candidate_zero_nodes=0,lsc_unit_candidate_zero_nodes_repaired=False,lsc_unit_layout_matches_stock_hal=True,
 lsc_stock_packed40_points_per_group=51,lsc_stock_extra_byte_after_each_group=True,
 lsc_unit_layout_evidence='../../reference/kernel320/stock-lsc-layout-validation.json')
p.write_text(json.dumps(d,indent=2)+'\n')
banner='320重要修正：本机原厂HAL每51个LSC点额外跳过1字节。按该规则解码后原4个零节点全部消失，无需补造／修复个体值；Python与C、主机和AArch64、两份读回一致。见reference/kernel320/README.md。golden有两种、基础表17种，真实模式选择／有效性／checksum及IPA接入仍待做。手机保持318，当前全部工具终态。\n\n'
for name in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md']:
 p=ROOT/name;s=p.read_text()
 if not s.startswith('320重要修正：'):p.write_text(banner+s)
for stage in [317,318,319]:
 p=ROOT/f'reference/kernel{stage}/README.md';s=p.read_text()
 note='320更新：[本机HAL分组规则](../kernel320/README.md)已解释此前4个零节点：每51点需额外跳过1字节，修正解码后均非零；没有补造或写回数据。原文中的零节点结论为当时错误候选布局的历史记录。\n\n'
 if not s.startswith('320更新：'):p.write_text(note+s)
mirror=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150')
paths=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths += [ROOT/n for n in ['NEXT-SESSION.md','NEXT-SESSION-PROMPT.md','linux-port/camera/deployment-lock.json']]
paths += [ROOT/f'reference/kernel{s}/README.md' for s in [317,318,319]]
for p in paths:
 target=mirror/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
print('Recorded target HAL framing correction; deployed318 unchanged.')
