"""
Adds `active_channels` and `return_signal` to TurboFDMSignalEncoder.encode_memory.
Backward compatible: with no arguments the encoder behaves exactly as before.

    python patch_nhop_source.py /workspace/FDM_PARAMETRIC/nhop_source.py

What changes (inside class TurboFDMSignalEncoder only):
  1. signature: encode_memory(self, memory, active_channels=None, return_signal=False)
  2. composite loop: skip any channel not in active_channels (carrier omitted entirely,
     NOT set to a_low, which would still be a live carrier)
  3. bits/max_bits are still computed for ALL channels, so samples_per_bit (the time
     segmentation of the remaining carriers) is unchanged
  4. return_signal=True returns (text, tokens, composite)
NOTE: normalization is per-sample min-max of the composite, so removing carriers
rescales the remaining ones. That is a real distribution shift for the host.
"""
import sys
import shutil

path = sys.argv[1] if len(sys.argv) > 1 else "/workspace/FDM_PARAMETRIC/nhop_source.py"
src = open(path).read()

start = src.index("class TurboFDMSignalEncoder")
end = src.index("HOP-CONTROLLED", start)
seg = src[start:end]

if "active_channels" in seg:
    print("already patched, nothing to do")
    sys.exit(0)


def rep(old, new):
    global seg
    n = seg.count(old)
    assert n == 1, f"expected exactly one match, found {n} for:\n{old}"
    seg = seg.replace(old, new)


rep("    def encode_memory(self, memory):",
    "    def encode_memory(self, memory, active_channels=None, return_signal=False):")

rep("        composite = np.zeros(self.num_tokens_per_encoder)\n",
    "        active_set = None if active_channels is None else set(active_channels)\n"
    "        composite = np.zeros(self.num_tokens_per_encoder)\n")

rep("            bits = all_bits[ch]\n            for bi, bit in enumerate(bits):",
    "            if active_set is not None and ch not in active_set:\n"
    "                continue\n"
    "            bits = all_bits[ch]\n            for bi, bit in enumerate(bits):")

rep("        return fdm_text, all_tokens\n",
    "        if return_signal:\n"
    "            return fdm_text, all_tokens, composite\n"
    "        return fdm_text, all_tokens\n")

shutil.copy(path, path + ".bak")
open(path, "w").write(src[:start] + seg + src[end:])
print(f"patched {path} (backup at {path}.bak)")
