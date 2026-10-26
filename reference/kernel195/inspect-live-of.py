from pathlib import Path
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
for name,tokens in [('drivers/of/dynamic.c',['phandle','OF_RECONFIG_ADD_PROPERTY']),('drivers/of/overlay.c',['phandle','of_resolve_phandles']),('drivers/of/base.c',['np->phandle','node->phandle']),('drivers/of/resolver.c',['phandle =']),('drivers/regulator/core.c',['regulator_register_supply_alias','regulator_get_alias','of_find_regulator_by_node'])]:
 lines=(k/name).read_text().splitlines();indices=[i for i,s in enumerate(lines) if any(v in s for v in tokens)]
 print(name)
 for i in indices:
  if name.endswith('overlay.c') and not any(v in lines[i] for v in ['phandle =','of_resolve_phandles','phandle"']):continue
  print('\n'.join(f'{j+1}: {lines[j]}' for j in range(max(0,i-2),min(len(lines),i+4))))
