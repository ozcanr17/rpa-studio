import os

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

from ..exceptions import VisionError
from ..os_facade.base import Rect

DEFAULT_LABELS = (
    "button", "checkbox", "combobox", "field", "icon", "image", "link",
    "menu", "radio", "scrollbar", "slider", "switch", "tab", "text", "window",
)
_KIND_ALIASES = {
    "any": "",
    "edit": "field",
    "input": "field",
    "textbox": "field",
    "text box": "field",
    "dropdown": "combobox",
    "select": "combobox",
    "combo box": "combobox",
    "check box": "checkbox",
    "radio button": "radio",
    "radiobutton": "radio",
    "push button": "button",
    "pushbutton": "button",
    "hyperlink": "link",
    "tab item": "tab",
    "tabitem": "tab",
    "menu item": "menu",
    "menuitem": "menu",
}
_PAD_VALUE = 114
_DEFAULT_MIN_SCORE = 0.35
_DEFAULT_IOU = 0.45


def normalize_kind(kind):
    key = str(kind or "").strip().lower()
    return _KIND_ALIASES.get(key, key)


def _read_labels(model_path, session):
    try:
        names = session.get_modelmeta().custom_metadata_map.get("names")
        if names:
            import ast
            parsed = ast.literal_eval(names)
            if isinstance(parsed, dict):
                return tuple(str(parsed[key]) for key in sorted(parsed))
            return tuple(str(name) for name in parsed)
    except Exception:
        pass
    path = os.path.splitext(str(model_path))[0] + ".labels"
    try:
        with open(path, "r", encoding="ascii", errors="replace") as handle:
            loaded = tuple(line.strip() for line in handle if line.strip())
        if loaded:
            return loaded
    except Exception:
        pass
    return DEFAULT_LABELS


def _read_config(model_path):
    path = os.path.splitext(str(model_path))[0] + ".json"
    try:
        import json
        with open(path, "r", encoding="ascii", errors="replace") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _nms(boxes, scores, floor, iou):
    if not boxes:
        return []
    try:
        picked = cv2.dnn.NMSBoxes(boxes, [float(score) for score in scores], float(floor), float(iou))
    except Exception:
        return list(range(len(boxes)))
    if picked is None or len(picked) == 0:
        return []
    return [int(np.asarray(index).flatten()[0]) for index in picked]


def _clamped(box, frame):
    fh, fw = frame.shape[:2]
    x, y, w, h = box
    x = max(0, min(int(round(x)), fw - 1))
    y = max(0, min(int(round(y)), fh - 1))
    w = max(1, min(int(round(w)), fw - x))
    h = max(1, min(int(round(h)), fh - y))
    return Rect(x, y, w, h)


class Detection:
    __slots__ = ("rect", "label", "score")

    def __init__(self, rect, label, score):
        self.rect = rect
        self.label = str(label)
        self.score = float(score)

    @property
    def center(self):
        return self.rect.center

    def __repr__(self):
        return "Detection(label={!r}, score={:.2f}, rect={!r})".format(self.label, self.score, self.rect)


class UIDetector:
    def __init__(self, model_path, labels=None, min_score=None, iou=None, providers=None):
        if cv2 is None or np is None:
            raise VisionError("opencv is required")
        if not model_path or not os.path.isfile(str(model_path)):
            raise VisionError("model not found: {}".format(model_path))
        try:
            import onnxruntime
        except ImportError:
            raise VisionError("onnxruntime is required")
        try:
            options = onnxruntime.SessionOptions()
            options.log_severity_level = 3
            wanted = list(providers) if providers else ["CPUExecutionProvider"]
            self._session = onnxruntime.InferenceSession(str(model_path), sess_options=options, providers=wanted)
        except Exception as exc:
            raise VisionError("cannot load model: {}".format(exc))
        config = _read_config(model_path)
        self._min_score = float(config.get("min_score", _DEFAULT_MIN_SCORE) if min_score is None else min_score)
        self._iou = float(config.get("iou", _DEFAULT_IOU) if iou is None else iou)
        spec = self._session.get_inputs()[0]
        self._input_name = spec.name
        shape = spec.shape
        self._height = shape[2] if isinstance(shape[2], int) else 640
        self._width = shape[3] if isinstance(shape[3], int) else 640
        self._labels = tuple(str(label) for label in labels) if labels else _read_labels(model_path, self._session)

    @property
    def labels(self):
        return self._labels

    def _label(self, index):
        index = int(index)
        return self._labels[index] if 0 <= index < len(self._labels) else "class" + str(index)

    def _letterbox(self, frame):
        image = frame if frame.ndim == 3 else cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        if image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        h, w = image.shape[:2]
        gain = min(self._width / float(w), self._height / float(h))
        nw, nh = max(1, int(round(w * gain))), max(1, int(round(h * gain)))
        pad_x = (self._width - nw) // 2
        pad_y = (self._height - nh) // 2
        canvas = np.full((self._height, self._width, 3), _PAD_VALUE, np.uint8)
        canvas[pad_y:pad_y + nh, pad_x:pad_x + nw] = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_LINEAR)
        blob = canvas[:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255.0
        return np.ascontiguousarray(blob), gain, pad_x, pad_y

    def _parse(self, out):
        out = np.squeeze(np.asarray(out))
        if out.ndim != 2:
            raise VisionError("unexpected model output shape")
        count = len(self._labels)
        wide = (count + 4, count + 5)
        if out.shape[0] in wide and out.shape[1] not in wide:
            out = out.T
        elif out.shape[0] < out.shape[1] and out.shape[1] > 1024:
            out = out.T
        cols = out.shape[1]
        if cols == count + 4:
            scores = out[:, 4:]
        elif cols >= 6:
            scores = out[:, 4:5] * out[:, 5:]
        else:
            raise VisionError("unexpected model output shape")
        return out[:, :4].astype(np.float32), scores

    def detect(self, frame, kind=None, min_score=None):
        if frame is None:
            raise VisionError("frame is None")
        floor = self._min_score if min_score is None else float(min_score)
        blob, gain, pad_x, pad_y = self._letterbox(frame)
        try:
            outputs = self._session.run(None, {self._input_name: blob})
        except Exception as exc:
            raise VisionError("inference failed: {}".format(exc))
        coords, scores = self._parse(outputs[0])
        ids = scores.argmax(axis=1)
        best = scores[np.arange(len(ids)), ids]
        mask = best >= floor
        coords, ids, best = coords[mask], ids[mask], best[mask]
        boxes = []
        for cx, cy, bw, bh in coords:
            boxes.append([
                (float(cx) - float(bw) / 2.0 - pad_x) / gain,
                (float(cy) - float(bh) / 2.0 - pad_y) / gain,
                float(bw) / gain,
                float(bh) / gain,
            ])
        wanted = normalize_kind(kind) if len(self._labels) > 1 else ""
        hits = []
        for index in _nms(boxes, best, floor, self._iou):
            label = self._label(ids[index])
            if wanted and wanted not in label.lower():
                continue
            hits.append(Detection(_clamped(boxes[index], frame), label, best[index]))
        hits.sort(key=lambda hit: -hit.score)
        return hits
