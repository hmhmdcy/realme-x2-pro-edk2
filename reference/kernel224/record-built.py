from pathlib import Path
import json
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel224')
state=json.loads((private/'r9-build-state-private.json').read_text());assert state['terminal'] and state['original214_files_links_modes_restored']
assert not Path(state['snapshot']).exists() and Path(state['original']).exists()
p=repo/'NEXT-SESSION.md';s=p.read_text().replace('RAW统计r9构建89779存活，原214保护在private/libcamera214-before224，终态须恢复。','RAW统计r9/r4的13包已构建，原214树已恢复；签名/实机待验。')
s=s.replace('原214的2254文件/链接/权限已保护；224构建89779存活，原树在private/libcamera214-before224，勿挪活编译树；候选r8保留223-built。','原214的2254文件/链接/权限已恢复，无待恢复快照；r9候选/work/libcamera224-built、r8缓存223-built保留。')
assert len(s.encode())<=6500;p.write_text(s)
p=here/'README.md';s=p.read_text().replace('r9/r4完整构建正在89779运行，保留原14补丁和全部子包。SDK原214树在private/libcamera214-before224，构建活跃时不能移动；终态需恢复并核对2254个文件/链接/模式。手机仍r8，候选未验收/部署。','r9/r4完整13包已构建，保留原14补丁和全部子包。SDK原214树2254个文件/链接/权限已恢复，无待恢复快照；完整签名/IPA及实机验证待完成。手机仍r8，候选未部署。');p.write_text(s)
p=private/'current-work-private.json';d=json.loads(p.read_text());d.update(state='r9/r4 complete13 built; original2142254 restored; signatures and physical candidate checks next',active_build_session=None,protected_original214_snapshot=None,candidate_retained_after_terminal=state['candidate']);p.write_text(json.dumps(d,indent=2)+'\n');print('K224_BUILD_TERMINAL_AND_ORIGINAL_RESTORE_RECORDED')
