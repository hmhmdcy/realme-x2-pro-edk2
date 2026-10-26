 if (result.parametersKnown && result.sensorControlsKnown) {
  IpeFrameObservation observation;
  observation.epoch=epoch;observation.sof=sof;observation.histogram=parsed.histogram;
  observation.population=parsed.population;observation.exposureLines=sensorContext.exposureLines;
  observation.gainCode=sensorContext.gainCode;observation.sensorSource=sensorContext.source;
  observation.exposureNs=std::llround(sensorContext.exposureLines*lineUs_*1000);
  observation.analogueGain=float(helper_->gain(sensorContext.gainCode));
  observation.ispRevision=result.ispRevision;observation.ifeGammaOverride=context->second.gammaEnabled;
  observation.luxValid=result.luxValid;observation.exposureIndex=result.exposureIndex;observation.luxIndex=result.luxIndex;
  uint64_t token=0;
  const int status=ipeHistory_.prepare(observation,&token);
  if (!status) {
   result.ipeToken=token;result.ipeHistogramTrace=histogramTrace(observation);
   result.exposureNs=observation.exposureNs;result.analogueGain=observation.analogueGain;
   LOG(IPACamss,Info)<<"IPE_OBSERVE epoch="<<epoch<<" sof="<<sof<<" token="<<token
    <<" trace="<<result.ipeHistogramTrace<<" population="<<observation.population
    <<" exposure-ns="<<observation.exposureNs<<" analogue-gain="<<observation.analogueGain
    <<" lines="<<observation.exposureLines<<" code="<<observation.gainCode<<" source="<<observation.sensorSource
    <<" revision="<<observation.ispRevision<<" lux-valid="<<observation.luxValid
    <<" exposure-index="<<observation.exposureIndex<<" gamma-override="<<observation.ifeGammaOverride;
  } else LOG(IPACamss,Error)<<"IPE observation rejected: "<<status;
 }
