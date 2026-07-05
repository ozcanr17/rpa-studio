try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

from ..exceptions import VisionError

_MIN_MATCHES = 10
_RATIO = 0.75
_INDEX_KDTREE = 1
_INDEX_LSH = 6
_DPI_FACTORS = (1.0, 1.25, 0.8, 1.5, 0.67, 2.0, 0.5, 3.0)
_EDGE_FACTORS = (1.0, 1.5, 0.67)
_CLAHE_STATE = {"clahe": None}


def _clahe():
    if _CLAHE_STATE["clahe"] is None:
        _CLAHE_STATE["clahe"] = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    return _CLAHE_STATE["clahe"]


def normalize_gray(image):
    if cv2 is None:
        raise VisionError("opencv is required")
    gray = FeatureMatcher._to_gray(image)
    try:
        return _clahe().apply(gray)
    except Exception:
        return gray


def edge_map(image):
    gray = normalize_gray(image)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(gx, gy)
    return cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)


class MatchResult:
    __slots__ = ("center", "corners", "bbox", "inliers", "scale")

    def __init__(self, center, corners, bbox, inliers, scale=1.0):
        self.center = center
        self.corners = corners
        self.bbox = bbox
        self.inliers = inliers
        self.scale = float(scale)

    def __repr__(self):
        return "MatchResult(center={}, inliers={}, scale={:.2f})".format(self.center, self.inliers, self.scale)


class FeatureMatcher:
    def __init__(self, detector="sift", min_matches=_MIN_MATCHES, ratio=_RATIO):
        if cv2 is None:
            raise VisionError("opencv is required")
        self._kind = detector.lower()
        self._min_matches = int(min_matches)
        self._ratio = float(ratio)
        self._detector = self._build_detector(self._kind)
        self._flann = self._build_flann(self._kind)

    @staticmethod
    def _build_detector(kind):
        if kind == "sift":
            return cv2.SIFT_create()
        if kind == "orb":
            return cv2.ORB_create(nfeatures=2000)
        raise VisionError("unknown detector: {}".format(kind))

    @staticmethod
    def _build_flann(kind):
        if kind == "orb":
            index_params = {"algorithm": _INDEX_LSH, "table_number": 6, "key_size": 12, "multi_probe_level": 1}
        else:
            index_params = {"algorithm": _INDEX_KDTREE, "trees": 5}
        return cv2.FlannBasedMatcher(index_params, {"checks": 50})

    def locate(self, template, scene, min_matches=None):
        needed = self._min_matches if min_matches is None else int(min_matches)
        last_error = "insufficient features"
        cache = {}
        plan = (
            (normalize_gray, (1.0,)),
            (edge_map, (1.0,)),
            (normalize_gray, _DPI_FACTORS[1:]),
            (edge_map, _EDGE_FACTORS[1:]),
        )
        for prep, factors in plan:
            if prep not in cache:
                try:
                    cache[prep] = (self._features(prep(scene)), prep(template))
                except Exception as exc:
                    last_error = str(exc)
                    cache[prep] = (None, None)
            scene_feats, tpl = cache[prep]
            if scene_feats is None:
                continue
            for factor in factors:
                work = self._rescale(tpl, factor)
                if work is None:
                    continue
                try:
                    return self._match_pair(work, scene_feats, needed, factor)
                except VisionError as exc:
                    last_error = str(exc)
        raise VisionError(last_error)

    def _features(self, image):
        kp, des = self._detector.detectAndCompute(image, None)
        if des is None or len(kp) < 2:
            return None
        return kp, des

    @staticmethod
    def _rescale(image, factor):
        if factor == 1.0:
            return image
        h, w = image.shape[:2]
        nw, nh = int(round(w * factor)), int(round(h * factor))
        if nw < 8 or nh < 8:
            return None
        return cv2.resize(image, (nw, nh), interpolation=cv2.INTER_CUBIC)

    def _match_pair(self, tpl, scene_feats, needed, factor):
        feats = self._features(tpl)
        if feats is None:
            raise VisionError("insufficient features")
        kp1, des1 = feats
        kp2, des2 = scene_feats
        des1, des2 = self._cast(des1, des2)
        good = self._ratio_test(self._flann.knnMatch(des1, des2, k=2))
        if len(good) < needed:
            raise VisionError("match count {} below {}".format(len(good), needed))
        return self._project(kp1, kp2, good, tpl.shape, factor)

    def _ratio_test(self, matches):
        good = []
        for pair in matches:
            if len(pair) == 2 and pair[0].distance < self._ratio * pair[1].distance:
                good.append(pair[0])
        return good

    def _project(self, kp1, kp2, good, tpl_shape, factor=1.0):
        src = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        dst = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
        matrix, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
        if matrix is None:
            raise VisionError("homography failed")
        h, w = tpl_shape[:2]
        corners = np.float32([[0, 0], [0, h], [w, h], [w, 0]]).reshape(-1, 1, 2)
        pts = cv2.perspectiveTransform(corners, matrix).reshape(-1, 2)
        xs, ys = pts[:, 0], pts[:, 1]
        bw = float(xs.max() - xs.min())
        bh = float(ys.max() - ys.min())
        if bw < 3.0 or bh < 3.0:
            raise VisionError("degenerate projection")
        aspect_ratio = (bw / bh) / (float(w) / max(1.0, float(h)))
        if aspect_ratio < 0.4 or aspect_ratio > 2.5:
            raise VisionError("implausible projection geometry")
        bbox = (float(xs.min()), float(ys.min()), bw, bh)
        center = (float(xs.mean()), float(ys.mean()))
        inliers = int(mask.sum()) if mask is not None else len(good)
        scale = factor * ((bw / max(1.0, float(w))) + (bh / max(1.0, float(h)))) / 2.0
        if scale < 0.15 or scale > 8.0:
            raise VisionError("implausible projection scale")
        return MatchResult(center, pts.tolist(), bbox, inliers, scale)

    def _cast(self, des1, des2):
        if self._kind == "orb":
            return des1, des2
        return des1.astype(np.float32), des2.astype(np.float32)

    @staticmethod
    def _to_gray(image):
        if image is None:
            raise VisionError("image is None")
        if image.ndim == 2:
            return image
        if image.shape[2] == 4:
            return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def load_image(path, flags=None):
    if cv2 is None:
        raise VisionError("opencv is required")
    image = cv2.imread(path, cv2.IMREAD_COLOR if flags is None else flags)
    if image is None:
        raise VisionError("cannot read image: {}".format(path))
    return image
