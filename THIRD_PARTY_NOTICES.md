# Third-party notices

The project license does not replace the licenses of its dependencies or copied
upstream material. The dependency versions below reflect the current `uv.lock`.
Packages are installed separately; their complete license and copyright notices
remain in their distributions. This table summarizes the main runtime packages,
not every transitive dependency or platform-specific binary component.

| Package | Version | Declared license | Upstream |
| --- | --- | --- | --- |
| ale-py | 0.11.2 | GPL-2.0-only | [Arcade Learning Environment](https://github.com/Farama-Foundation/Arcade-Learning-Environment) |
| gymnasium | 1.3.0 | MIT | [Gymnasium](https://github.com/Farama-Foundation/Gymnasium) |
| numpy | 2.5.3 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | [NumPy](https://github.com/numpy/numpy) |
| httpx | 0.28.1 | BSD-3-Clause | [HTTPX](https://github.com/encode/httpx) |
| imageio | 2.37.4 | BSD-2-Clause | [ImageIO](https://github.com/imageio/imageio) |
| imageio-ffmpeg | 0.6.0 | BSD-2-Clause (Python wrapper) | [imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg) |

The `imageio-ffmpeg` wrapper's license does not describe all rights or obligations
for the FFmpeg executable it invokes or distributes. FFmpeg licensing depends on
the build; preserve the relevant binary distribution's notices when redistributing
it. See [FFmpeg licensing](https://ffmpeg.org/legal.html).

Atari game ROMs and game audiovisual content retain their respective owners'
rights. They are not relicensed by this project. Jev is an external service, not
a model implementation or set of weights distributed under the project license.

## OCAtari-derived Pong object extraction

The Pong RAM mapping and vision color definitions in `src/jev_atari/observation.py`
are adapted from OCAtari at revision
`99c874675df6b76a33a80b57776c123fbcd051af`:

- https://github.com/k4ntz/OC_Atari/blob/99c874675df6b76a33a80b57776c123fbcd051af/ocatari/ram/pong.py
- https://github.com/k4ntz/OC_Atari/blob/99c874675df6b76a33a80b57776c123fbcd051af/ocatari/vision/pong.py

The full OCAtari package is not installed. The extraction is Pong-specific, fixed,
and supplies semantic object observations, not a general learned visual encoder.

### Upstream license

MIT License

Copyright (c) 2023 Quentin Delfosse, Jannis Blüml, Belal Alkufri, Bjarne Gregori, Christopher Schubert, Sebastian Gräfe, Timo Holst

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## OCAtari-derived Seaquest calibration mapping

`src/jev_atari/seaquest.py` adapts the RAM mappings from the same MIT-licensed
OCAtari revision `99c874675df6b76a33a80b57776c123fbcd051af`:

- https://github.com/k4ntz/OC_Atari/blob/99c874675df6b76a33a80b57776c123fbcd051af/ocatari/ram/seaquest.py

The copyright and full permission notice above also apply to this adaptation.
The full OCAtari package is not installed. This mapping is experimental and its
local calibration does not establish complete semantic accuracy.

The v2 observation diagnostics in `src/jev_atari/seaquest_observation.py` also
adapt color definitions from the same revision's `ocatari/vision/seaquest.py`.
The same MIT notice applies; color support is not complete semantic validation.

## OCAtari-derived Freeway mapping

`src/jev_atari/freeway.py` adapts coordinates, lane layout and colors from
https://github.com/k4ntz/OC_Atari/blob/99c874675df6b76a33a80b57776c123fbcd051af/ocatari/ram/freeway.py
under the full MIT license and copyright notice reproduced above. OCAtari is not
installed. The local bounded pixel-support validation does not establish precise
collision geometry, visible sprites at the left boundary, or an optimal policy.
