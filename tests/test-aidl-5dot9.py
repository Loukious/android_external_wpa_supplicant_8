#!/usr/bin/env python3
"""Compile the fixed-channel AIDL fragment and check primary direction/scope."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
source = (root / 'hostapd/aidl/hostapd.cpp').read_text()
start = source.index('\t\tif (band == band5Ghz && sec_channel &&')
opening = source.index('{', start)
depth = 0
for end in range(opening, len(source)):
    depth += (source[end] == '{') - (source[end] == '}')
    if not depth:
        fragment = source[start:end + 1]
        break
program = r'''
#include <string>
#include <cassert>
#include <cstdio>
static void configure(int band, int channel, int &sec_channel, std::string &config) {
 const int band5Ghz = 2;
 struct { int channel; } channelParams{channel};
 auto &ht_cap_vht_oper_he_oper_eht_oper_chwidth_as_string = config;
''' + fragment + r'''
}
int main() {
 for (int band: {1,2,4,8,3}) for (int channel: {1,9,14,149,153,165,169,173,177,181})
 for (int secondary: {0,1,-1}) {
  int actual=secondary;
  const std::string before = secondary ? "ht_capab=[HT40+]\nvht_oper_chwidth=1\nhe_oper_chwidth=1\n"
                                       : "vht_oper_chwidth=0\nhe_oper_chwidth=0\n";
  auto config=before;
  configure(band,channel,actual,config);
  if(band==2 && secondary && (channel==169 || channel==177)) {
   assert(actual==-1);
   assert(channel+4*actual==(channel==169?165:173));
   assert(config=="ht_capab=[HT40-]\nvht_oper_chwidth=1\nhe_oper_chwidth=1\n");
  } else { assert(actual==secondary); assert(config==before); }
 }
 puts("150 cases: upper primary direction, 20 MHz, other channels/bands and preserved VHT/HE: OK");
}
'''
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory)
    (path / 'test.cpp').write_text(program)
    subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=undefined', str(path / 'test.cpp'), '-o', str(path / 'test')], check=True)
    subprocess.run([str(path / 'test')], check=True)
