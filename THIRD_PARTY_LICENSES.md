# Third-party licenses

Taala's only runtime dependency is **zxcvbn** (the Python port by Daniel Wolf, version 4.5.0,
https://github.com/dwolfhub/zxcvbn-python), installed from PyPI and not copied into this
repository. Taala is not affiliated with or endorsed by Dropbox or the port's maintainers.
Its bundled frequency lists (English words, names, common passwords) come with the package;
Taala reads them but does not redistribute them.

Development-only dependencies (`pytest`, `openpyxl`) are not part of what Taala ships.

---

MIT License

Copyright (c) 2016 Daniel Wolf

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
