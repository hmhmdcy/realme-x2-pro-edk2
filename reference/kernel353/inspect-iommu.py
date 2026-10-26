"""Inspect the prepared target kernel's reservation APIs before alias mapping."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
build=storage.mounted_build();source=(build/'source').resolve()
paths=['drivers/iommu/of_iommu.c','drivers/iommu/iommu.c','drivers/iommu/dma-iommu.c','drivers/iommu/arm/arm-smmu/arm-smmu.c','include/linux/iommu.h']
records=[];snippets={}
for path in paths:
 text=(source/path).read_text();records.append(dict(path=path,sha256=hashlib.sha256(text.encode()).hexdigest()))
 if path.endswith('of_iommu.c'):
  assert 'if (phys->start >= phys->end)' in text and 'return IOMMU_RESV_RESERVED;' in text
  assert '"memory-region"' in text and '"iommu-addresses"' in text
 if path=='drivers/iommu/iommu.c':
  start=text.index('void iommu_get_resv_regions(');snippet=text[start:text.index('\n}',start)+2]
  snippets['get_reservations']=snippet;assert 'ops->get_resv_regions' in snippet
 if path=='drivers/iommu/arm/arm-smmu/arm-smmu.c':
  start=text.index('static void arm_smmu_get_resv_regions(');snippet=text[start:text.index('\n}',start)+2]
  snippets['arm_smmu_get_reservations']=snippet;assert 'iommu_dma_get_resv_regions' in snippet
 if path.endswith('dma-iommu.c'):
  start=text.index('void iommu_dma_get_resv_regions(');snippet=text[start:text.index('\n}',start)+2]
  snippets['dma_get_reservations']=snippet;assert 'of_iommu_get_resv_regions' in snippet
  start=text.index('static int iova_reserve_iommu_regions(');snippet=text[start:text.index('\n}',start)+2]
  snippets['dma_reserve_iova']=snippet;assert 'reserve_iova' in snippet and 'iommu_get_resv_regions' in snippet
  snippets['reservation_lines']=[l for l in text.splitlines() if 'reserve_iova' in l or 'IOMMU_RESV_RESERVED' in l]
symbols={l.split()[1]:l.split()[2] for l in (build/'Module.symvers').read_text().splitlines()}
exports={name:symbols.get(name) for name in ['iommu_get_domain_for_dev','iommu_get_dma_domain','iommu_get_resv_regions','iommu_put_resv_regions','iommu_map','iommu_unmap','iommu_iova_to_phys']}
config=(build/'.config').read_text();assert 'CONFIG_IOMMU_DMA=y' in config and 'CONFIG_ARM64_4K_PAGES=y' in config
assert all(value for name,value in exports.items() if name!='iommu_get_dma_domain'),exports
(P/'iommu-planning-snippets-private.json').write_text(json.dumps(snippets,indent=2)+'\n')
report=dict(stage=353,source=str(source),sources=records,exports=exports,
 no_physical_reg_iommu_addresses_node_becomes_reserved_iova_only=True,
 reservation_flows_through_core_and_dma_allocator=True,
 planned_firmware_alias=dict(start=0,bytes=5*1024*1024),
 proposed_method='Reserve firmware IOVA window through standard OF memory-region/iommu-addresses; obtain the current domain with exported iommu_get_domain_for_dev, verify it is a DMA domain, allocate coherent RAM elsewhere and map its pages at reserved A5 addresses.',
 iommu_get_dma_domain_is_not_exported_to_modules=exports['iommu_get_dma_domain'] is None,
 no_physical_reserved_camera_carveout_required_by_this_proposal=True,
 hardware_domain_grouping_and_live_alias_mapping_not_yet_verified=True,
 no_dt_or_iommu_kernel_change_made=True,phone_changed=False,passed=True)
(HERE/'iommu-planning-evidence.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
