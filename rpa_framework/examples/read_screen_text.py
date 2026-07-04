corner = Region(0, 0, 800, 200)
words = corner.text()
print("the top-left corner of your screen says:")
print(words if words else "(no text recognized - is Tesseract installed or bundled in vendor/?)")
