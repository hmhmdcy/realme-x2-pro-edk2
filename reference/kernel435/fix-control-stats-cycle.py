"""Drain receipts while a requested control waits for its older ISP packet."""
from pathlib import Path
import hashlib,json
import storage
HERE=Path(__file__).resolve().parent;T=storage.candidate()/'src/libcamera-v0.7.2';D=T/'src/ipa/camss-vfe'
def edit(p,a,b):
 t=p.read_text();assert t.count(a)==1,(str(p),a,t.count(a));p.write_text(t.replace(a,b))
p=D/'camss.cpp'
edit(p,'GtmHistory gtmHistory_;','GtmHistory gtmHistory_;\n bool ispControlsWaiting_ = false;')
edit(p,'if (pendingWhiteBalance_ || !preparedParameters_.empty() || parameterHistory_.empty()) return -EAGAIN;','''if (pendingWhiteBalance_ || !preparedParameters_.empty() || parameterHistory_.empty()) {ispControlsWaiting_=true;return -EAGAIN;}
 ispControlsWaiting_=false;''')
edit(p,'pendingTone_.reset();committedTone_.reset();gtmHistory_.reset();proposedGtm_.reset();frameGtms_.clear();\n epoch_ = epoch;','pendingTone_.reset();committedTone_.reset();gtmHistory_.reset();proposedGtm_.reset();frameGtms_.clear();ispControlsWaiting_=false;\n epoch_ = epoch;')
edit(p,'numericHistory_.stop();pendingTone_.reset();committedTone_.reset();gtmHistory_.reset();proposedGtm_.reset();frameGtms_.clear();','numericHistory_.stop();pendingTone_.reset();committedTone_.reset();gtmHistory_.reset();proposedGtm_.reset();frameGtms_.clear();ispControlsWaiting_=false;')
edit(p,'if (af_.state()!=ipa::ContrastAf::State::Scanning && result.parametersKnown && context==std::prev(parameterHistory_.end()) &&','if (!ispControlsWaiting_ && af_.state()!=ipa::ContrastAf::State::Scanning && result.parametersKnown && context==std::prev(parameterHistory_.end()) &&')
edit(p,'if(tracksGtm() && observation.luxValid && af_.state()!=ipa::ContrastAf::State::Scanning &&','if(tracksGtm() && !ispControlsWaiting_ && observation.luxValid && af_.state()!=ipa::ContrastAf::State::Scanning &&')
p=T/'src/libcamera/pipeline/camss-vfe/camss_vfe.cpp'
edit(p,'''  if (ret == -EAGAIN) {
   ispControls_.push_front(std::move(request));
   return;
  }''','''  if (ret == -EAGAIN) {
   ispControls_.push_front(std::move(request));
   /* Its older ISP update can only be ACKed by processing statistics.
    * Keep draining them, then retry controls ahead of new auto proposals. */
   break;
  }''')
s=json.loads((HERE/'source-state.json').read_text())
for row in s['source_hashes']:row['sha256']=hashlib.sha256((T/row['path']).read_bytes()).hexdigest()
(HERE/'source-state.json').write_text(json.dumps(s,indent=2)+'\n')
