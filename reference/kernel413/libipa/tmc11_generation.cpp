/* SPDX-License-Identifier: LGPL-2.1-or-later */
#include "tmc11_generation.h"
#include <algorithm>
#include <cmath>
#include <cstring>

namespace libcamera::ipa {
namespace {
float mul(float a, float b) { volatile float result = a * b; return result; }
template<std::size_t N> bool finite(const std::array<float,N> &v)
{
	return std::all_of(v.begin(),v.end(),[](float x){ return std::isfinite(x); });
}
uint32_t index(float gain)
{
	if (gain <= 1) return 0;
	return std::min(uint32_t(std::round(std::log(gain)/std::log(1.03f))),94U);
}
float inverseGamma(float target, const std::array<float,257> &gamma, unsigned &hi)
{
	for (; hi < 257; ++hi) {
		if (target <= gamma[hi]) {
			float left = mul(gamma[hi] - target,float(hi-1));
			float right = mul(target - gamma[hi-1],float(hi));
			return (left + right) / (gamma[hi] - gamma[hi-1]);
		}
	}
	return 256;
}
void preprocess(const Tmc11Region &p, const std::array<uint32_t,1024> &raw,
		std::array<float,1024> &hist)
{
	float total = 0;
	for (uint32_t v : raw) total += float(v);
	float maximum = mul(p.histogramClipSlope,total)/1024;
	float clipped = 0;
	for (unsigned i=0;i<1024;++i) {
		float value = float(raw[i]);
		hist[i] = value < maximum ? value : maximum;
		if (value >= maximum) clipped += value - maximum;
	}
	if (hist[0] > hist[1]) { clipped += hist[0]-hist[1]; hist[0]=hist[1]; }
	float average = clipped/1024;
	for (float &v : hist) v += average;
	for (unsigned pass=0;pass<4;++pass) {
		for (unsigned i=0;i<1024;++i) {
			hist[i] = mul(hist[i],p.histogramKernel[0]);
			for (unsigned k=1;k<5;++k) {
				hist[i] += mul(hist[std::min(i+k,1023U)],p.histogramKernel[k]);
				hist[i] += mul(hist[i<k?0:i-k],p.histogramKernel[k]);
			}
		}
	}
}
void histogramKnees(const Tmc11Region &p,float drcGain,const std::array<float,257> &gamma,
		    const std::array<float,1024> &hist,const std::array<float,1024> &weights,
		    std::array<float,5> &x,std::array<float,5> &y)
{
	float total=0;
	for(float v:hist) total+=v;
	float sum=0,lowSum=0,lowCount=0,midSum=0,midCount=0,highSum=0,highCount=0;
	for(unsigned i=0;i<1024;++i) {
		sum += hist[i];
		float value=mul(hist[i],weights[i]);
		if(sum>=mul(total,p.suppressStart) && sum<=mul(total,p.suppressEnd)) {highSum+=value;highCount+=hist[i];}
		if(sum>=mul(total,p.boostStart) && sum<=mul(total,p.boostEnd)) {lowSum+=value;lowCount+=hist[i];}
		if(sum>=mul(total,p.averageStart) && sum<=mul(total,p.averageEnd)) {midSum+=value;midCount+=hist[i];}
	}
	float low=lowCount?std::exp(lowSum/lowCount):0;
	float mid=midCount?std::exp(midSum/midCount):0;
	float high=highCount?std::exp(highSum/highCount):0;
	unsigned hi=1;
	float target=std::clamp(mul(p.toneTargets[2],1023),0.0f,1023.0f);
	float key=inverseGamma(target,gamma,hi)/256;
	float highAdapt=mul(p.stretchBright,high)+mul(1-p.stretchBright,16383);
	float lowAdapt=mul(p.stretchDark,low)+mul(1-p.stretchDark,0);
	float contrast=(mul(std::log(mid+1),2)-std::log(lowAdapt+1)-std::log(highAdapt+1)) /
		      (std::log(highAdapt+1)-std::log(lowAdapt+1));
	float adjusted=mul(key,std::pow(contrast>0?p.toneBrightAdjustment:p.toneDarkAdjustment,contrast));
	float global=adjusted/(mid/16383);
	float lower=drcGain/p.histogramEnhanceClamp,upper=mul(drcGain,p.histogramEnhanceClamp);
	global=global<lower?lower:(global>upper?upper:global);
	float darkAdjusted=mul(global,p.contrastDarkAdjustment);
	float highAdjusted=mul(p.contrastBrightClip,2)-global;
	highAdjusted=highAdjusted<=1?1:(highAdjusted>global?global:highAdjusted);
	x={0,low/16383,mid/16383,high/16383,1};
	y={0,mul(x[1],darkAdjusted),mul(x[2],global),mul(x[3],highAdjusted),1};
}
void coefficients(Tmc11PchipCurve &p)
{
	std::array<float,4> h,delta;
	std::array<float,5> d{};
	for(unsigned i=0;i<4;++i) {h[i]=p.x[i+1]-p.x[i];delta[i]=(p.y[i+1]-p.y[i])/h[i];}
	for(unsigned i=1;i<4;++i) {
		float w1=mul(2,h[i])+h[i-1],w2=h[i]+mul(2,h[i-1]);
		d[i]=(w1+w2)/(w1/delta[i-1]+w2/delta[i]);
	}
	float endpoint=(mul(mul(2,h[3])+h[2],delta[3])-mul(h[3],delta[2]))/(h[2]+h[3]);
	d[4]=mul(delta[2],delta[3])<0 && std::abs(endpoint)>std::abs(mul(3,delta[3]))?mul(3,delta[3]):
		(mul(endpoint,delta[3])<0?0:endpoint);
	for(unsigned i=1;i<4;++i) {
		p.coefficient[(i-1)*3]=d[i];
		p.coefficient[(i-1)*3+1]=(mul(3,delta[i])-mul(2,d[i])-d[i+1])/h[i];
		p.coefficient[(i-1)*3+2]=((d[i]-mul(2,delta[i])+d[i+1])/h[i])/h[i];
	}
}
} /* namespace */

bool generateTmc11Curve(const Tmc11Region &p,float drc,float dark,
		       const std::array<float,257> &gamma,const std::array<float,1024> &weights,
		       const std::array<uint32_t,1024> *histogram,Tmc11GenerationResult *output)
{
	static_assert(sizeof(Tmc11Region)==176 && sizeof(Tmc11GenerationResult)==8288);
	std::array<float,44> fields;std::memcpy(fields.data(),&p,sizeof p);
	if(!output || !finite(fields) || !std::isfinite(drc) || !std::isfinite(dark) || drc<=0 || dark<0 ||
	   !finite(gamma) || !finite(weights) || gamma[0]<0 || gamma[256]>1023 || !std::is_sorted(gamma.begin(),gamma.end()))
		return false;
	float gain=std::pow(1.03f,float(index(drc)));
	float ratio=std::clamp(mul(dark-1,p.darkBoostRatio)+1+p.reserve[0],1.0f,16.0f);
	Tmc11GenerationResult result{};
	result.darkGain=mul(gain,ratio);
	float maxPercentage=std::min(std::log(8.0f)/std::log(std::pow(1.03f,float(index(result.darkGain)))),1.0f);
	result.ltm.percentage=p.ltmPercentage;result.gtmPercentage=p.gtmPercentage;
	result.ltm.bright=p.contrastHEBright;result.ltm.dark=p.contrastHEDark;
	if(result.ltm.percentage>maxPercentage) {result.ltm.percentage=maxPercentage;result.gtmPercentage=1-maxPercentage;}
	if(std::abs(double(ratio-1))<1e-9) ratio=1.0001f;
	/* The target's lower clamp bound is this same quotient. Its compiled
	 * clamp consequently preserves finite quotients even above anchor1;
	 * the pinned helper's min-like behavior does not match this target. */
	float darkY=p.toneAnchors[2]/ratio;
	std::array<float,5> anchorX={0,darkY/result.darkGain,p.toneAnchors[2]/gain,p.toneAnchors[3],1};
	std::array<float,5> anchorY={0,darkY,p.toneAnchors[2],p.toneAnchors[3],1};
	std::array<float,5> histX,histY;histX.fill(1);histY.fill(1);
	if(histogram) {
		preprocess(p,*histogram,result.processedHistogram);
		histogramKnees(p,drc,gamma,result.processedHistogram,weights,histX,histY);
	}
	for(unsigned i=0;i<5;++i) {
		result.pchip.x[i]=mul(p.histogramEnhanceRatio[i],histX[i])+mul(1-p.histogramEnhanceRatio[i],anchorX[i]);
		result.pchip.y[i]=mul(p.histogramEnhanceRatio[i],histY[i])+mul(1-p.histogramEnhanceRatio[i],anchorY[i]);
	}
	coefficients(result.pchip);
	if(histogram) {
		std::array<float,1024> cdf;cdf[0]=result.processedHistogram[0];
		for(unsigned i=1;i<1024;++i) cdf[i]=cdf[i-1]+result.processedHistogram[i];
		unsigned hi=1;
		for(unsigned i=0;i<1024;++i) {
			float target=std::clamp(mul(cdf[i]/cdf[1023],1023),0.0f,1023.0f);
			result.contrastCurve[i]=inverseGamma(target,gamma,hi)/256;
		}
	} else {
		/* The target calls memset with byte1, rather than filling float1. */
		std::memset(result.contrastCurve.data(),1,sizeof result.contrastCurve);
	}
	std::array<float,2072> all;std::memcpy(all.data(),&result,sizeof result);
	if(!finite(all)) return false;
	*output=result;
	return true;
}
} /* namespace libcamera::ipa */
