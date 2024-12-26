<details><summary><i>Naming history (click to expand)</i></summary>
<pre>
2023 Mar 01: 245-Improved-Digital-Jammer.md
2023 May 22: 022_Improved_Digital_Jammer.md
</pre>
</details>

# Improved Digital Jammer

ℹ️ This material coincides with material from SDR slideshow F (all slides).

This digital jammer is more effective than the original because it can match the symbol rate of the target.

```

GUI Range

Constellation Object

Variable


Random source  ⟶  Constellation modulator  ⟶  Rational Resampler      ⟶  Osmocom sink
                                                                      ⟶  Waterfall sink
                                                                      ⟶  Time sink
```

- Variable `samp_rate`: Same as PSK_Digital_Jammer
- Variable (a new variable block):
  - Id: `symbol_rate`
  - Value: `100e3`
- Rational Resampler:
  - Interpolation: `int(samp_rate)`
  - Decimation: `int(symbol_rate)`
- Time Sink:
  - Y min: `-2`
  - Y max: `2`
- All other parameters:
  - Same as the normal digital jammer.
