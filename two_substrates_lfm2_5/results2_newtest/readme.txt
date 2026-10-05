t's running correctly. Here's what that run is doing, step by step.

The setup. The host is the frozen LFM2.5-1.2B model that was fine-tuned to read 40-channel FDM memory blocks. It has 16 layers, but only 6 of them are attention layers. The memory has 32 queryable channels (8 to 39). This run splits them in half: the 16 even channels are Block A, the 16 odd channels are Block B.

What the host sees. Each training example is a random memory. Block B's 16 carriers, plus the never-queried channels 0 to 7, are encoded into the signal and become the token block in the prompt. Block A's 16 carriers are left out of the signal entirely. The leak check you see at the top proves that: changing Block A values changes nothing in the tokens, 30 out of 30 times.

Where Block A goes instead. A small 10.3M-parameter write head takes the 16 Block A values and emits a fake KV cache for 513 positions in front of the prompt, but only for the 6 attention layers. The 10 conv layers get nothing. The host then answers the question "What is the risk assessment?" and is expected to produce its assessment followed by the full Context: TEAM=..., REGION=..., ... list of all 32 channels. To get the even channels right it has to read them out of the fake cache, because they exist nowhere else.

What's being trained. Only the write head. The host never changes. For 15000 steps the loss is cross-entropy on the answer tokens, and the one difference from the earlier run is the assessment tokens in loss part of the header: the host's own assessment sentence is now a target too, not masked out. That penalizes a head whose prefix garbles the preamble, which is what happened at this split last time.

What's evaluated afterward. Two passes of 200 memories each. First with the matched prefix, scoring each channel's first NAME=VALUE in the answer. Then the control: the same memory in context, but the prefix built from a different random memory. If Block A accuracy collapses to the 26 percent chance level under the swap while Block B holds, the host was genuinely reading Block A from the prefix.

Why only this cell. The 4/28 and 8/24 splits were already clean. 16/16 is where the prefix started corrupting the host's output and one seed degraded Block B, so this reruns just that split for all three seeds into lfm25_la16, leaving the original results in place for comparison.

Each seed takes roughly 90 minutes. Paste the stage-7 summary when it's done.
