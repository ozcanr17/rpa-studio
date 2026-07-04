try:
    import gi
    gi.require_version("Atspi", "2.0")
    from gi.repository import Atspi
except (ImportError, ValueError):
    Atspi = None

from .base import AccessibilityInspector, UIElement, register_inspector
from ..os_facade.base import Rect
from ..exceptions import BackendError

_STATES = ("focused", "focusable", "enabled", "visible", "showing", "selected", "checked", "editable", "sensitive")


@register_inspector("linux")
class AtspiInspector(AccessibilityInspector):
    def __init__(self):
        if Atspi is None:
            raise BackendError("Atspi (PyGObject + at-spi2) is required on Linux")
        Atspi.init()
        self._coord = Atspi.CoordType.SCREEN

    def root(self):
        return self._wrap(Atspi.get_desktop(0))

    def element_at(self, x, y):
        target = self._hit(Atspi.get_desktop(0), int(x), int(y))
        return self._wrap(target) if target is not None else None

    def focused_element(self):
        for node in self._raw_children(Atspi.get_desktop(0)):
            found = self._focused_in(node)
            if found is not None:
                return self._wrap(found)
        return None

    def children(self, element):
        return [self._wrap(c) for c in self._raw_children(element.native)]

    def _hit(self, acc, x, y):
        component = self._component(acc)
        if component is None:
            return None
        try:
            rect = component.get_extents(self._coord)
        except Exception:
            return None
        if not self._inside(rect, x, y):
            return None
        best = acc
        for child in self._raw_children(acc):
            deeper = self._hit(child, x, y)
            if deeper is not None:
                best = deeper
        return best

    def _focused_in(self, acc):
        try:
            states = acc.get_state_set()
        except Exception:
            states = None
        if states is not None and states.contains(Atspi.StateType.FOCUSED):
            return acc
        for child in self._raw_children(acc):
            found = self._focused_in(child)
            if found is not None:
                return found
        return None

    def _wrap(self, acc):
        if acc is None:
            return None
        return UIElement(
            backend="linux",
            role=self._safe(acc.get_role_name),
            name=self._safe(acc.get_name),
            automation_id=self._automation_id(acc),
            class_name=self._attr(acc, "class"),
            value=self._value(acc),
            states=self._state_names(acc),
            bounding_box=self._extents(acc),
            process_id=self._pid(acc),
            native=acc,
        )

    @staticmethod
    def _raw_children(acc):
        kids = []
        try:
            count = acc.get_child_count()
        except Exception:
            return kids
        for i in range(count):
            try:
                child = acc.get_child_at_index(i)
            except Exception:
                child = None
            if child is not None:
                kids.append(child)
        return kids

    @staticmethod
    def _component(acc):
        try:
            return acc.get_component_iface()
        except Exception:
            return None

    def _extents(self, acc):
        component = self._component(acc)
        if component is None:
            return None
        try:
            rect = component.get_extents(self._coord)
        except Exception:
            return None
        return Rect(rect.x, rect.y, rect.width, rect.height)

    def _automation_id(self, acc):
        for key in ("automation-id", "id", "name"):
            value = self._attr(acc, key)
            if value:
                return value
        return ""

    @staticmethod
    def _attr(acc, key):
        try:
            attrs = acc.get_attributes()
        except Exception:
            return ""
        if not attrs:
            return ""
        return attrs.get(key, "")

    @staticmethod
    def _value(acc):
        try:
            text_iface = acc.get_text_iface()
        except Exception:
            text_iface = None
        if text_iface is None:
            return ""
        try:
            return text_iface.get_text(0, text_iface.get_character_count())
        except Exception:
            return ""

    @staticmethod
    def _state_names(acc):
        names = []
        try:
            state_set = acc.get_state_set()
        except Exception:
            return tuple(names)
        if state_set is None:
            return tuple(names)
        for name in _STATES:
            state = getattr(Atspi.StateType, name.upper(), None)
            if state is None:
                continue
            try:
                if state_set.contains(state):
                    names.append(name)
            except Exception:
                continue
        return tuple(names)

    @staticmethod
    def _pid(acc):
        try:
            return int(acc.get_process_id())
        except Exception:
            return None

    @staticmethod
    def _inside(rect, x, y):
        return rect.x <= x <= rect.x + rect.width and rect.y <= y <= rect.y + rect.height

    @staticmethod
    def _safe(getter):
        try:
            return getter() or ""
        except Exception:
            return ""
