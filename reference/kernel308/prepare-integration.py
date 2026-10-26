"""Extend the existing hardware IPA/pipeline with RGB AWB and revisioned WB."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
def edit(name,before,after):
    p=HERE/name;s=p.read_text()
    assert s.count(before)==1,(name,before[:75],s.count(before))
    p.write_text(s.replace(before,after))

edit('camss.mojom','struct Statistics {','''struct AutoIspUpdate {
\tbool valid;
\tuint32 revision;
\tdouble red;
\tdouble blue;
};
struct Statistics {''')
edit('camss.mojom',' AutoSensorUpdate automaticUpdate;',''' AutoSensorUpdate automaticUpdate;
\tAutoIspUpdate ispUpdate;
\tuint32 ispRevision;
\tbool rgbPresent;
\tuint32 awbRegions;
\tarray<double> rgbMeans;''')
edit('camss.mojom','prepareParameters(uint64 epoch, uint32 bufferId)',
     'prepareParameters(uint64 epoch, uint32 bufferId, uint32 revision)')
edit('camss.mojom','parametersApplied(uint64 epoch, uint32 firstSof)',
     'parametersApplied(uint64 epoch, uint32 firstSof, uint32 revision)')
edit('ipa/meson.build',"'hardware_agc.cpp'","'hardware_agc.cpp', 'hardware_awb.cpp'")
edit('ipa/parameter_encoder.h','/* Serialize only supported blocks',
'''int effectiveColourGains(const ResidualBlackProfile &profile, double red, double blue,
\t\t\t double *effectiveRed, double *effectiveBlue);

/* Serialize only supported blocks''')
edit('ipa/parameter_encoder.cpp','int encodeParameters(Span<uint8_t> output,',
'''int effectiveColourGains(const ResidualBlackProfile &profile, double red, double blue,
\t\t\t double *effectiveRed, double *effectiveBlue)
{
\tuint16_t r, g, b;
\tif (!effectiveRed || !effectiveBlue ||
\t    gainQ10(red * profile.normalization, &r) ||
\t    gainQ10(profile.normalization, &g) ||
\t    gainQ10(blue * profile.normalization, &b))
\t\treturn -ERANGE;
\t/* VFE175 converts the common U15Q10 fields to U12Q7. */
\tconst unsigned int rq7 = std::min<unsigned int>((r + 4) >> 3, 4095);
\tconst unsigned int gq7 = std::min<unsigned int>((g + 4) >> 3, 4095);
\tconst unsigned int bq7 = std::min<unsigned int>((b + 4) >> 3, 4095);
\tif (!gq7)
\t\treturn -ERANGE;
\t*effectiveRed = double(rq7) / gq7;
\t*effectiveBlue = double(bq7) / gq7;
\treturn 0;
}

int encodeParameters(Span<uint8_t> output,''')
edit('ipa/parameter_encoder.cpp','#include <cerrno>','#include <algorithm>\n#include <cerrno>')

IPA='ipa/camss.cpp'
edit(IPA,'#include "hardware_agc.h"','#include "hardware_agc.h"\n#include "hardware_awb.h"\n#include "statistics.h"')
edit(IPA,'int prepareParameters(uint64_t epoch, uint32_t id, uint32_t *bytesused)',
     'int prepareParameters(uint64_t epoch, uint32_t id, uint32_t revision, uint32_t *bytesused)')
edit(IPA,'void parametersApplied(uint64_t epoch, uint32_t firstSof)',
     'void parametersApplied(uint64_t epoch, uint32_t firstSof, uint32_t revision)')
edit(IPA,' std::unique_ptr<HardwareAgc> agc_;',''' std::unique_ptr<HardwareAgc> agc_;
\tstd::unique_ptr<HardwareAwb> awb_;
\tbool awbEnabled_ = false;
\tuint32_t ispRevision_ = 0;
\tstd::optional<AutoIspUpdate> pendingWhiteBalance_;
\tstruct ParameterContext { uint32_t revision; double red, blue; };
\tstd::map<uint32_t, ParameterContext> preparedParameters_, parameterHistory_;''')
# Reset optional AWB each time tuning is reconfigured.
p=HERE/IPA;s=p.read_text().replace('agc_.reset(); autoAvailable_ = false;',
                                 'agc_.reset(); awb_.reset(); autoAvailable_ = false;');p.write_text(s)
edit(IPA,'  { &controls::ColourGains, ControlInfo(0.0f, 8.0f, 1.0f) },',
'''  { &controls::ColourGains, ControlInfo(0.0f, 8.0f, 1.0f) },
  { &controls::AwbEnable, ControlInfo(false, false, false) },''')
edit(IPA,'  profile_ = { *subtraction, *normalization };',
'''  profile_ = { *subtraction, *normalization };
  const auto &awb = (*root)["awb"];
  if (!awb.isEmpty()) {
   auto candidate = std::make_unique<HardwareAwb>();
   if (!awb.isDictionary() || candidate->initialise(awb)) return -EINVAL;
   awb_ = std::move(candidate);
   ControlInfoMap::Map map;
   for (const auto &[id, value] : *ipaControls) map.emplace(id, value);
   map[&controls::AwbEnable] = ControlInfo(false, true, false);
   *ipaControls = ControlInfoMap(std::move(map), controls::controls);
  }''')
edit(IPA,'  if (id == controls::ColourGains.id() && startup) continue;',
'''  if (id == controls::ColourGains.id() && startup) continue;
  if (id == controls::AwbEnable.id()) {
   if (value.type() != ControlTypeBool || value.isArray()) return -EINVAL;
   if (!startup && value.get<bool>() != awbEnabled_) return -ENOTSUP;
   continue;
  }''')
edit(IPA,'\tdouble red = 1, blue = 1;',
'''\tconst bool awbEnabled = controls.get(controls::AwbEnable).value_or(false);
\tif (awbEnabled && !awb_) return -ENOTSUP;
\tdouble red = 1, blue = 1;''')
edit(IPA,'\tred_ = red; blue_ = blue;',
'''\tred_ = red; blue_ = blue;
\tawbEnabled_ = awbEnabled;
\tispRevision_ = 0;
\tpendingWhiteBalance_.reset();
\tpreparedParameters_.clear(); parameterHistory_.clear();
\tif (awb_) awb_->reset();''')
edit(IPA,' automatic_ = false; awaiting_.reset();',
''' automatic_ = false; awaiting_.reset();
\tawbEnabled_ = false; pendingWhiteBalance_.reset();
\tpreparedParameters_.clear(); parameterHistory_.clear();''')
edit(IPA,'int IPACamss::prepareParameters(uint64_t epoch, uint32_t id, uint32_t *bytesused)',
     'int IPACamss::prepareParameters(uint64_t epoch, uint32_t id, uint32_t revision, uint32_t *bytesused)')
edit(IPA,'''\tsize_t used;
\tint ret = encodeParameters(it->second.memory->planes()[0], profile_, red_, blue_, input_, Rectangle(input_), &used);
\tif (!ret)
\t\t*bytesused = used;
\treturn ret;''',
'''\tif (preparedParameters_.count(revision)) return -EALREADY;
\tdouble red = red_, blue = blue_;
\tif (revision) {
\t\tif (!pendingWhiteBalance_ || pendingWhiteBalance_->revision != revision) return -ESTALE;
\t\tred = pendingWhiteBalance_->red; blue = pendingWhiteBalance_->blue;
\t} else if (!parameterHistory_.empty()) return -ESTALE;
\tdouble effectiveRed, effectiveBlue;
\tint ret = effectiveColourGains(profile_, red, blue, &effectiveRed, &effectiveBlue);
\tif (ret) return ret;
\tsize_t used;
\tret = encodeParameters(it->second.memory->planes()[0], profile_, red, blue, input_, Rectangle(input_), &used);
\tif (!ret) {
\t\tpreparedParameters_[revision] = { revision, effectiveRed, effectiveBlue };
\t\t*bytesused = used;
\t}
\treturn ret;''')
p=HERE/IPA;s=p.read_text();a=s.index('void IPACamss::parametersApplied(');b=s.index('void IPACamss::processStats(',a)
s=s[:a]+'''void IPACamss::parametersApplied(uint64_t epoch, uint32_t firstSof, uint32_t revision)
{
\tif (!running_ || epoch != epoch_) return;
\tauto it = preparedParameters_.find(revision);
\tif (it == preparedParameters_.end() ||
\t    (!parameterHistory_.empty() &&
\t     (firstSof <= parameterHistory_.rbegin()->first || revision <= parameterHistory_.rbegin()->second.revision))) {
\t\tLOG(IPACamss, Error) << "Invalid ISP parameter acknowledgement revision=" << revision;
\t\treturn;
\t}
\tparameterHistory_[firstSof] = it->second;
\tpreparedParameters_.erase(it);
\tif (pendingWhiteBalance_ && pendingWhiteBalance_->revision == revision) pendingWhiteBalance_.reset();
\twhile (parameterHistory_.size() > 64) parameterHistory_.erase(parameterHistory_.begin());
\tLOG(IPACamss, Info) << "ISP applied epoch=" << epoch << " revision=" << revision << " first-sof=" << firstSof;
}

'''+s[b:];p.write_text(s)
a=s.index('\tconstexpr size_t expected =',s.index('void IPACamss::processStats'));b=s.index(' if (sensorContext.valid',a)
s=s[:a]+'''\tconst auto &memory = it->second.memory->planes()[0];
\tif (bytesused > memory.size()) { result.status = -EINVAL; complete(); return; }
\tif (lastStats_ && sof <= *lastStats_) {
\t\tresult.status = sof == *lastStats_ ? -EALREADY : -ERANGE; complete(); return;
\t}
\tParsedStatistics parsed;
\tresult.status = parseStatistics({ memory.data(), bytesused }, input_.width, input_.height, &parsed);
\tif (result.status) { complete(); return; }
\tlastStats_ = sof;
\tresult.population = parsed.population;
\tresult.weightedSum = parsed.weightedSum;
\tresult.rgbPresent = !parsed.grid.regions.empty();
\tauto context = parameterHistory_.upper_bound(sof);
\tif (context != parameterHistory_.begin()) {
\t\t--context;
\t\tresult.parametersKnown = true;
\t\tresult.ispRevision = context->second.revision;
\t\tconst std::array<float, 2> gains{ float(context->second.red), float(context->second.blue) };
\t\tmetadata.set(controls::ColourGains, Span<const float, 2>(gains));
\t}
\teffective_ = result.parametersKnown;
\tmetadata.set(controls::AwbEnable, awbEnabled_);
\tif (awbEnabled_ && effective_ && result.rgbPresent && context == std::prev(parameterHistory_.end()) &&
\t    !pendingWhiteBalance_ && preparedParameters_.empty()) {
\t\tauto awb = awb_->calculate(parsed.grid, context->second.red, context->second.blue);
\t\tresult.awbRegions = awb.regions;
\t\tresult.rgbMeans = { awb.means.r(), awb.means.g(), awb.means.b() };
\t\tmetadata.set(controls::AwbLocked, awb.locked);
\t\tif (awb.valid && ispRevision_ < UINT32_MAX - 1) {
\t\t\tdouble red, blue;
\t\t\tif (!effectiveColourGains(profile_, awb.red, awb.blue, &red, &blue) &&
\t\t\t    (red != context->second.red || blue != context->second.blue)) {
\t\t\t\tpendingWhiteBalance_ = AutoIspUpdate{ true, ++ispRevision_, awb.red, awb.blue };
\t\t\t\tresult.ispUpdate = *pendingWhiteBalance_;
\t\t\t}
\t\t}
\t}
\tLOG(IPACamss, Info) << "RGB epoch=" << epoch << " sof=" << sof << " present=" << result.rgbPresent
\t\t<< " regions=" << result.awbRegions << " revision=" << result.ispRevision
\t\t<< " parameters-known=" << result.parametersKnown;
'''+s[b:];s=s.replace('agc_->calculate(histogram.bins,','agc_->calculate(parsed.histogram,');p.write_text(s)

PIPE='pipeline/camss_vfe.cpp'
edit(PIPE,'\tvoid paramsReady(FrameBuffer *buffer);',
'''\tvoid paramsReady(FrameBuffer *buffer);
\tvoid queueIspUpdate(const ipa::camss::AutoIspUpdate &update);''')
edit(PIPE,'\tbool paramsApplied_ = false;',
'''\tbool paramsApplied_ = false;
\tbool parameterBusy_ = false, ispHealthy_ = true;
\tuint32_t parameterRevision_ = 0, lastIspRevision_ = 0;''')
edit(PIPE,' for (auto &buffer : d->paramsBuffers_) {\n  uint32_t used = 0;',
''' d->parameterBusy_ = false; d->ispHealthy_ = true;
 d->parameterRevision_ = d->lastIspRevision_ = 0;
 for (auto &buffer : d->paramsBuffers_) {
  uint32_t used = 0;''')
edit(PIPE,'d->ipa_->prepareParameters(d->epoch_, buffer->cookie(), &used)',
     'd->ipa_->prepareParameters(d->epoch_, buffer->cookie(), 0, &used)')
edit(PIPE,'''  ret = d->params_->queueBuffer(buffer.get());
  if (ret) goto error;
 }''','''  ret = d->params_->queueBuffer(buffer.get());
  if (ret) goto error;
  d->parameterBusy_ = true;
 }''')
edit(PIPE,'''\tif (!running_ || buffer->metadata().status != FrameMetadata::FrameSuccess)
\t\treturn;
\tparamsApplied_ = true;''','''\tif (!running_) return;
\tparameterBusy_ = false;
\tif (buffer->metadata().status != FrameMetadata::FrameSuccess) {
\t\tispHealthy_ = false;
\t\tLOG(CamssVfe, Error) << "ISP parameter buffer failed";
\t\treturn;
\t}
\tparamsApplied_ = true;''')
edit(PIPE,'ipa_->parametersApplied(epoch_, firstParamSof_);',
     'ipa_->parametersApplied(epoch_, firstParamSof_, parameterRevision_);')
edit(PIPE,'<< " first-sof=" << firstParamSof_;',
     '<< " first-sof=" << firstParamSof_ << " revision=" << parameterRevision_;')
edit(PIPE,'void CamssVfeData::frameStart(uint32_t sequence)',
'''void CamssVfeData::queueIspUpdate(const ipa::camss::AutoIspUpdate &update)
{
\tif (!running_ || !ispHealthy_ || !update.valid) return;
\tif (parameterBusy_ || update.revision != lastIspRevision_ + 1 ||
\t    !std::isfinite(update.red) || !std::isfinite(update.blue) ||
\t    update.red < .125 || update.red > 8 || update.blue < .125 || update.blue > 8) {
\t\tispHealthy_ = false;
\t\tLOG(CamssVfe, Error) << "Rejected ISP gain proposal";
\t\treturn;
\t}
\tFrameBuffer *buffer = paramsBuffers_[0].get();
\tparameterBusy_ = true;
\tuint32_t used = 0;
\tint ret = ipa_->prepareParameters(epoch_, buffer->cookie(), update.revision, &used);
\tif (!ret) {
\t\tauto &metadata = buffer->_d()->metadata();
\t\tmetadata.status = FrameMetadata::FrameSuccess;
\t\tmetadata.planes()[0].bytesused = used;
\t\tret = params_->queueBuffer(buffer);
\t}
\tif (ret) {
\t\tparameterBusy_ = false; ispHealthy_ = false;
\t\tLOG(CamssVfe, Error) << "ISP parameter queue failed: " << ret;
\t\treturn;
\t}
\tparameterRevision_ = lastIspRevision_ = update.revision;
\tLOG(CamssVfe, Info) << "WB queue epoch=" << epoch_ << " revision=" << update.revision
\t\t<< " red=" << update.red << " blue=" << update.blue;
}

void CamssVfeData::frameStart(uint32_t sequence)''')
edit(PIPE,'#include <chrono>','#include <chrono>\n#include <cmath>')
edit(PIPE,' if (!running_ || !paramsApplied_) return;',
     ' if (!running_ || !paramsApplied_ || parameterBusy_) return;')
edit(PIPE,' pendingStats_.erase(it);\n',
''' pendingStats_.erase(it);
 queueIspUpdate(statistics.ispUpdate);
 LOG(CamssVfe, Info) << "WB context epoch=" << epoch << " sof=" << sof << " revision=" << statistics.ispRevision
  << " known=" << statistics.parametersKnown;
''')
print('Prepared revisioned RGB IPA and pipeline source.')
