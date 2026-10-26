#include "gamma_curve.h"
#include <cstdio>
#include <cstdint>
using namespace libcamera::ipa;
int main(int argc, char **argv)
{
 if (argc != 3)
  return 2;
 FILE *in = fopen(argv[1], "rb"), *out = fopen(argv[2], "wb");
 if (!in || !out)
  return 2;
 GammaCurve curve;
 while (fread(curve.data(), sizeof(float), curve.size(), in) == curve.size()) {
  GammaLut lut{};
  uint32_t valid = encodeGammaCurve(curve, &lut);
  if (fwrite(&valid, sizeof(valid), 1, out) != 1 ||
      fwrite(lut.data(), sizeof(uint32_t), lut.size(), out) != lut.size())
   return 3;
 }
 int failed = ferror(in);
 fclose(in);
 return fclose(out) || failed ? 3 : 0;
}
