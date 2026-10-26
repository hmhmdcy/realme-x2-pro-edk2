"""Pin generated Titan170 protocol definitions privately; export numeric facts only."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,re,urllib.request
import host
ROOT=Path(__file__).resolve().parent
urls=[
 'https://raw.githubusercontent.com/Hozzu/TFLite-aarch64-linux-with-delegate/b60c3300678c6d7102810d30414e296c0b2335ce/onboard/home/pkshin/include/camx/titan170_ife.h',
 'https://raw.githubusercontent.com/comprehensive9/vendor_qcom_proprietary/36fc163a534963a5b3af52186af5efcc63401ad2/prebuilt_HY11/target/product/kona/obj/include/camx/titan17x/titan170_ife.h']
def fetch(item):
 i,url=item;p=host.PRIVATE/f'titan170-ife-source-{i}-private.h'
 if not p.exists():p.write_bytes(urllib.request.urlopen(url,timeout=30).read())
 b=p.read_bytes();assert len(b)==1245272 and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()=='bd94210d738d3a3b947231a16f33e03601cbf33a'
 return b,dict(url=url,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),git_blob='bd94210d738d3a3b947231a16f33e03601cbf33a')
with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(fetch,enumerate(urls)))
assert rows[0][0]==rows[1][0]
text=rows[0][0].decode();facts={}
for line in text.splitlines():
 if line.startswith('#define ') and re.search(r'regIFE_IFE_0_VFE_DMI_(?:CFG|ADDR|DATA)|VFE_DMI_CFG_(?:DMI_RAM_SEL_MASK|AUTO_INC|AUTO_LOAD)|VFE_MODULE_STATS_(?:CGC_OVERRIDE|EN)_SKIN_BHIST|VFE_STATS_BHIST',line):
  match=re.match(r'#define\s+(\w+)\s+(0x[0-9a-fA-F]+|\d+)\b',line)
  if match:facts[match[1]]=int(match[2],0)
 match=re.match(r'\s*(IFE_IFE_0_VFE_DMI_CFG_DMI_RAM_SEL_STATS_BHIST_RAM)\s*=\s*(0x[0-9a-fA-F]+)\b',line)
 if match:facts[match[1]]=int(match[2],0)
report=dict(stage=296,sources=[r[1] for r in rows],two_independent_repository_blobs_identical=True,numeric_protocol_definitions=facts,no_vendor_implementation_copied=True,no_hardware_operation=True)
(ROOT/'dmi-protocol-sources.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
