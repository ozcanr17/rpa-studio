try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

from ..exceptions import VisionError
from ..os_facade.base import Rect

_KINDS = {
    "button": (1.0, 9.0, 16, 90),
    "field": (2.2, 50.0, 14, 64),
    "any": (0.2, 60.0, 10, 400),
}


def _kind_spec(kind):
    return _KINDS.get(str(kind).lower(), _KINDS["any"])


def _to_gray(frame):
    if frame.ndim == 2:
        return frame
    return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


def _dedupe(boxes):
    kept = []
    for box in sorted(boxes, key=lambda b: b.width * b.height):
        cx, cy = box.center
        twin = False
        for other in kept:
            ox, oy = other.center
            if abs(ox - cx) <= 4 and abs(oy - cy) <= 4 and other.width * other.height * 1.4 >= box.width * box.height:
                twin = True
                break
        if not twin:
            kept.append(box)
    return kept


def find_ui_regions(frame, kind="any"):
    if cv2 is None or np is None:
        raise VisionError("opencv is required")
    aspect_min, aspect_max, h_min, h_max = _kind_spec(kind)
    gray = _to_gray(frame)
    edges = cv2.Canny(gray, 40, 140)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 3))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
    contours = cv2.findContours(closed, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)[0]
    boxes = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if h < h_min or h > h_max or w < 12:
            continue
        aspect = w / float(max(1, h))
        if aspect < aspect_min or aspect > aspect_max:
            continue
        if cv2.contourArea(contour) < 0.55 * w * h:
            continue
        epsilon = min(0.04 * cv2.arcLength(contour, True), 0.6 * min(w, h))
        approx = cv2.approxPolyDP(contour, epsilon, True)
        if len(approx) < 4 or len(approx) > 8:
            continue
        boxes.append(Rect(x, y, w, h))
    return _dedupe(boxes)


def find_ui(frame, kind="any", text=None, ocr=None):
    boxes = find_ui_regions(frame, kind)
    if not text:
        return boxes
    if ocr is None:
        raise VisionError("an OCR engine is required to filter by text")
    needle = str(text).strip().lower()
    hits = []
    for box in boxes:
        crop = frame[max(0, box.y - 2):box.y + box.height + 2, max(0, box.x - 2):box.x + box.width + 2]
        try:
            if needle in ocr.read_text(crop).lower():
                hits.append(box)
        except Exception:
            continue
    return hits
