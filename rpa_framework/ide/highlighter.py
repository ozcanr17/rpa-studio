import keyword
import re

from .directives import IMAGE_PATTERN
from .qt_shim import cached_builder

_COLORS = {
    "keyword": ("#f92672", True),
    "builtin": ("#66d9ef", False),
    "definition": ("#a6e22e", False),
    "number": ("#ae81ff", False),
    "string": ("#e6db74", False),
    "comment": ("#75715e", False),
    "decorator": ("#fd971f", False),
    "directive": ("#a1efe4", True),
}

_RULES = (
    (re.compile(r"\b(" + "|".join(keyword.kwlist) + r")\b"), "keyword"),
    (re.compile(r"\b(self|cls)\b"), "builtin"),
    (re.compile(r"\b(?:def|class)\s+(\w+)"), "definition"),
    (re.compile(r"\b[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b"), "number"),
    (re.compile(r"@\w+(?:\.\w+)*"), "decorator"),
    (re.compile(r"\"[^\"\\\n]*(?:\\.[^\"\\\n]*)*\"|'[^'\\\n]*(?:\\.[^'\\\n]*)*'"), "string"),
    (re.compile(r"#[^\n]*"), "comment"),
)


@cached_builder
def build_highlighter_class(qt):
    QtGui = qt.QtGui

    def make_format(color, bold):
        fmt = QtGui.QTextCharFormat()
        fmt.setForeground(QtGui.QColor(color))
        if bold:
            fmt.setFontWeight(QtGui.QFont.Weight.Bold)
        return fmt

    class PythonHighlighter(QtGui.QSyntaxHighlighter):
        def __init__(self, document):
            super().__init__(document)
            self._formats = {name: make_format(color, bold) for name, (color, bold) in _COLORS.items()}

        def highlightBlock(self, text):
            self.setCurrentBlockState(0)
            if IMAGE_PATTERN.match(text):
                self.setFormat(0, len(text), self._formats["directive"])
                return
            for pattern, name in _RULES:
                for match in pattern.finditer(text):
                    start, end = match.span(1) if pattern.groups else match.span()
                    self.setFormat(start, end - start, self._formats[name])
            self._triple(text, "'''", 1)
            self._triple(text, '"""', 2)

        def _triple(self, text, delim, state):
            fmt = self._formats["string"]
            start = 0
            if self.previousBlockState() == state:
                end = text.find(delim)
                if end < 0:
                    self.setCurrentBlockState(state)
                    self.setFormat(0, len(text), fmt)
                    return
                self.setFormat(0, end + 3, fmt)
                start = end + 3
            index = text.find(delim, start)
            while index >= 0:
                end = text.find(delim, index + 3)
                if end < 0:
                    self.setCurrentBlockState(state)
                    self.setFormat(index, len(text) - index, fmt)
                    return
                self.setFormat(index, end + 3 - index, fmt)
                index = text.find(delim, end + 3)

    return PythonHighlighter
