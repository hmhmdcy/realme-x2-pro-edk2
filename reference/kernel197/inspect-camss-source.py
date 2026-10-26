from pathlib import Path
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
for name,markers in [('drivers/media/platform/qcom/camss/camss.c',['static int camss_of_parse_endpoint_node','static int camss_of_parse_ports','static int camss_probe']),('drivers/media/v4l2-core/v4l2-fwnode.c',['static int v4l2_fwnode_endpoint_parse_csi2_bus','int v4l2_fwnode_endpoint_alloc_parse'])]:
 s=(k/name).read_text();print(name)
 for marker in markers:
  start=s.find(marker);print(s[start:start+5000] if start>=0 else marker+' NOT FOUND')
