try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

try:
    import pytesseract
    from pytesseract import Output
except ImportError:
    pytesseract = None
    Output = None

from ..exceptions import OCRError


class TextBox:
    __slots__ = ("text", "confidence", "left", "top", "width", "height")

    def __init__(self, text, confidence, left, top, width, height):
        self.text = text
        self.confidence = float(confidence)
        self.left = int(left)
        self.top = int(top)
        self.width = int(width)
        self.height = int(height)

    @property
    def center(self):
        return (self.left + self.width // 2, self.top + self.height // 2)

    def __repr__(self):
        return "TextBox({!r}, conf={:.1f})".format(self.text, self.confidence)


class OCREngine:
    def __init__(self, lang="eng", tessdata_dir=None, tesseract_cmd=None, psm=3, oem=3, preprocess=True):
        if pytesseract is None:
            raise OCRError("pytesseract is required")
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        self._lang = lang
        self._tessdata_dir = tessdata_dir
        self._psm = int(psm)
        self._oem = int(oem)
        self._preprocess = bool(preprocess)

    def _config(self, extra=None):
        parts = ["--oem", str(self._oem), "--psm", str(self._psm)]
        if self._tessdata_dir:
            parts += ["--tessdata-dir", self._tessdata_dir]
        if extra:
            parts.append(extra)
        return " ".join(parts)

    def read_text(self, image, extra_config=None):
        try:
            return pytesseract.image_to_string(self._prepare(image), lang=self._lang, config=self._config(extra_config)).strip()
        except Exception as exc:
            raise OCRError(str(exc))

    def read_boxes(self, image, min_confidence=0.0, extra_config=None):
        try:
            data = pytesseract.image_to_data(self._prepare(image), lang=self._lang, config=self._config(extra_config), output_type=Output.DICT)
        except Exception as exc:
            raise OCRError(str(exc))
        return self._collect(data, float(min_confidence))

    def locate_text(self, image, needle, min_confidence=0.0):
        target = needle.strip().lower()
        for box in self.read_boxes(image, min_confidence):
            if target in box.text.lower():
                return box
        return None

    def available_languages(self):
        try:
            return list(pytesseract.get_languages(config=self._config()))
        except Exception as exc:
            raise OCRError(str(exc))

    @staticmethod
    def _collect(data, min_confidence):
        boxes = []
        for i in range(len(data.get("text", []))):
            text = data["text"][i].strip()
            if not text:
                continue
            try:
                conf = float(data["conf"][i])
            except (TypeError, ValueError):
                conf = -1.0
            if conf < min_confidence:
                continue
            boxes.append(TextBox(text, conf, data["left"][i], data["top"][i], data["width"][i], data["height"][i]))
        return boxes

    def _prepare(self, image):
        if not self._preprocess or cv2 is None or np is None or not isinstance(image, np.ndarray):
            return image
        gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        height = gray.shape[0]
        if 0 < height < 40:
            factor = min(4, max(2, int(round(80.0 / max(1, height)))))
            gray = cv2.resize(gray, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)
        try:
            gray = cv2.bilateralFilter(gray, 5, 40, 40)
        except Exception:
            pass
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary
