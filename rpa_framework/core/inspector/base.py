import abc
import json
import platform

from ..os_facade.base import Rect
from ..exceptions import BackendError, ElementNotFoundError

_REGISTRY = {}
_ALIASES = {"Linux": "linux", "Windows": "windows"}


def register_inspector(name):
    def decorator(cls):
        _REGISTRY[name] = cls
        return cls
    return decorator


class UIElement:
    __slots__ = (
        "backend",
        "role",
        "name",
        "automation_id",
        "class_name",
        "value",
        "states",
        "bounding_box",
        "process_id",
        "native",
    )

    def __init__(self, backend, role="", name="", automation_id="", class_name="", value="", states=(), bounding_box=None, process_id=None, native=None):
        self.backend = backend
        self.role = role
        self.name = name
        self.automation_id = automation_id
        self.class_name = class_name
        self.value = value
        self.states = tuple(states)
        self.bounding_box = bounding_box
        self.process_id = process_id
        self.native = native

    def to_dict(self):
        box = self.bounding_box.as_tuple() if isinstance(self.bounding_box, Rect) else None
        return {
            "backend": self.backend,
            "role": self.role,
            "name": self.name,
            "automation_id": self.automation_id,
            "class_name": self.class_name,
            "value": self.value,
            "states": list(self.states),
            "bounding_box": box,
            "process_id": self.process_id,
        }

    def to_json(self, indent=2):
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    def matches(self, role=None, name=None, automation_id=None):
        if role is not None and role.lower() not in self.role.lower():
            return False
        if name is not None and name.lower() not in self.name.lower():
            return False
        if automation_id is not None and automation_id != self.automation_id:
            return False
        return True

    def __repr__(self):
        return "UIElement(role={!r}, name={!r}, id={!r})".format(self.role, self.name, self.automation_id)


class AccessibilityInspector(abc.ABC):
    @abc.abstractmethod
    def root(self):
        raise NotImplementedError

    @abc.abstractmethod
    def element_at(self, x, y):
        raise NotImplementedError

    @abc.abstractmethod
    def focused_element(self):
        raise NotImplementedError

    @abc.abstractmethod
    def children(self, element):
        raise NotImplementedError

    def deepest_at(self, x, y, max_depth=32):
        current = self.element_at(x, y)
        depth = 0
        while current is not None and depth < max_depth:
            try:
                kids = self.children(current)
            except Exception:
                break
            best = None
            for child in kids:
                box = getattr(child, "bounding_box", None)
                if box is None or not box.contains(x, y):
                    continue
                if best is None or box.width * box.height < best.bounding_box.width * best.bounding_box.height:
                    best = child
            if best is None:
                break
            current = best
            depth += 1
        return current

    def walk(self, element=None, max_depth=64):
        start = element or self.root()
        stack = [(start, 0)]
        while stack:
            current, depth = stack.pop()
            if current is None:
                continue
            yield current
            if depth >= max_depth:
                continue
            for child in reversed(self.children(current)):
                stack.append((child, depth + 1))

    def find(self, role=None, name=None, automation_id=None, element=None, max_depth=64):
        for node in self.walk(element, max_depth):
            if node.matches(role=role, name=name, automation_id=automation_id):
                return node
        raise ElementNotFoundError("no element for role={!r} name={!r} id={!r}".format(role, name, automation_id))

    def find_all(self, role=None, name=None, automation_id=None, element=None, max_depth=64):
        return [n for n in self.walk(element, max_depth) if n.matches(role=role, name=name, automation_id=automation_id)]


class InspectorFactory:
    @classmethod
    def create(cls, backend=None):
        key = backend or _ALIASES.get(platform.system())
        if key is None:
            raise BackendError("unsupported platform: {}".format(platform.system()))
        cls._load(key)
        impl = _REGISTRY.get(key)
        if impl is None:
            raise BackendError("no inspector registered for '{}'".format(key))
        return impl()

    @staticmethod
    def _load(key):
        if key == "linux":
            from . import linux_inspector
        elif key == "windows":
            from . import windows_inspector
        else:
            raise BackendError("no loader for inspector '{}'".format(key))
