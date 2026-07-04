class RPAError(Exception):
    pass


class BackendError(RPAError):
    pass


class ElementNotFoundError(RPAError):
    pass


class VisionError(RPAError):
    pass


class OCRError(RPAError):
    pass
