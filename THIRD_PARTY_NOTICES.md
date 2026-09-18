# OCAtari-derived Pong object extraction

The Pong RAM mapping and vision color definitions in `src/jev_atari/observation.py`
are adapted from OCAtari at revision
`99c874675df6b76a33a80b57776c123fbcd051af`:

- https://github.com/k4ntz/OC_Atari/blob/99c874675df6b76a33a80b57776c123fbcd051af/ocatari/ram/pong.py
- https://github.com/k4ntz/OC_Atari/blob/99c874675df6b76a33a80b57776c123fbcd051af/ocatari/vision/pong.py

The full OCAtari package is not installed. The extraction is Pong-specific, fixed,
and supplies semantic object observations, not a general learned visual encoder.

## Upstream license

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
