from .base import AccessibilityInspector, UIElement, register_inspector
from ..os_facade.base import Rect, prepare_com_codegen
from ..exceptions import BackendError

try:
    import comtypes
    import comtypes.client
    from ctypes.wintypes import POINT
    prepare_com_codegen()
    comtypes.client.GetModule("UIAutomationCore.dll")
    from comtypes.gen.UIAutomationClient import CUIAutomation, IUIAutomation
except Exception:
    comtypes = None
    CUIAutomation = None
    IUIAutomation = None
    POINT = None

_CONTROL_TYPES = {
    50000: "Button",
    50001: "Calendar",
    50002: "CheckBox",
    50003: "ComboBox",
    50004: "Edit",
    50005: "Hyperlink",
    50006: "Image",
    50007: "ListItem",
    50008: "List",
    50009: "Menu",
    50010: "MenuBar",
    50011: "MenuItem",
    50012: "ProgressBar",
    50013: "RadioButton",
    50014: "ScrollBar",
    50015: "Slider",
    50016: "Spinner",
    50017: "StatusBar",
    50018: "Tab",
    50019: "TabItem",
    50020: "Text",
    50021: "ToolBar",
    50022: "ToolTip",
    50023: "Tree",
    50024: "TreeItem",
    50025: "Custom",
    50026: "Group",
    50027: "Thumb",
    50028: "DataGrid",
    50029: "DataItem",
    50030: "Document",
    50031: "SplitButton",
    50032: "Window",
    50033: "Pane",
    50034: "Header",
    50035: "HeaderItem",
    50036: "Table",
    50037: "TitleBar",
    50038: "Separator",
}

_STATE_FLAGS = ("IsEnabled", "IsOffscreen", "IsKeyboardFocusable", "HasKeyboardFocus")

_GEN = None


def _gen():
    global _GEN
    if _GEN is None:
        from comtypes.gen import UIAutomationClient as gen
        _GEN = gen
    return _GEN


def _pattern(element, pid_name, iface_name):
    gen = _gen()
    obj = element.GetCurrentPattern(getattr(gen, pid_name))
    if not obj:
        return None
    return obj.QueryInterface(getattr(gen, iface_name))


def _value_of(element):
    for pid, iface in (("UIA_ValuePatternId", "IUIAutomationValuePattern"), ("UIA_LegacyIAccessiblePatternId", "IUIAutomationLegacyIAccessiblePattern")):
        try:
            pattern = _pattern(element, pid, iface)
            if pattern is not None:
                value = pattern.CurrentValue
                if value:
                    return str(value)[:2000]
        except Exception:
            continue
    return ""


def _pattern_states(element):
    names = []
    try:
        pattern = _pattern(element, "UIA_TogglePatternId", "IUIAutomationTogglePattern")
        if pattern is not None:
            state = int(pattern.CurrentToggleState)
            if state == 1:
                names.append("checked")
            elif state == 2:
                names.append("indeterminate")
    except Exception:
        pass
    try:
        pattern = _pattern(element, "UIA_SelectionItemPatternId", "IUIAutomationSelectionItemPattern")
        if pattern is not None and pattern.CurrentIsSelected:
            names.append("selected")
    except Exception:
        pass
    try:
        pattern = _pattern(element, "UIA_ExpandCollapsePatternId", "IUIAutomationExpandCollapsePattern")
        if pattern is not None:
            names.append("expanded" if int(pattern.CurrentExpandCollapseState) == 1 else "collapsed")
    except Exception:
        pass
    return names


@register_inspector("windows")
class UIAInspector(AccessibilityInspector):
    def __init__(self):
        if comtypes is None or CUIAutomation is None:
            raise BackendError("comtypes and UIAutomationCore are required on Windows")
        self._uia = comtypes.client.CreateObject(CUIAutomation, interface=IUIAutomation)
        self._walker = self._uia.RawViewWalker

    def root(self):
        return self._wrap(self._uia.GetRootElement())

    def element_at(self, x, y):
        try:
            element = self._uia.ElementFromPoint(POINT(int(x), int(y)))
        except Exception:
            return None
        return self._wrap(element)

    def focused_element(self):
        try:
            return self._wrap(self._uia.GetFocusedElement())
        except Exception:
            return None

    def children(self, element):
        kids = []
        try:
            child = self._walker.GetFirstChildElement(element.native)
        except Exception:
            child = None
        while child:
            kids.append(self._wrap(child))
            try:
                child = self._walker.GetNextSiblingElement(child)
            except Exception:
                child = None
        return kids

    def _wrap(self, element):
        if element is None:
            return None
        return UIElement(
            backend="windows",
            role=self._control_type(element),
            name=self._prop(element, "CurrentName"),
            automation_id=self._prop(element, "CurrentAutomationId"),
            class_name=self._prop(element, "CurrentClassName"),
            value=_value_of(element),
            states=self._states(element),
            bounding_box=self._rect(element),
            process_id=self._pid(element),
            native=element,
        )

    @staticmethod
    def _control_type(element):
        try:
            code = int(element.CurrentControlType)
        except Exception:
            return ""
        return _CONTROL_TYPES.get(code, str(code))

    @staticmethod
    def _prop(element, attr):
        try:
            return getattr(element, attr) or ""
        except Exception:
            return ""

    @staticmethod
    def _rect(element):
        try:
            r = element.CurrentBoundingRectangle
        except Exception:
            return None
        return Rect(r.left, r.top, r.right - r.left, r.bottom - r.top)

    @staticmethod
    def _pid(element):
        try:
            return int(element.CurrentProcessId)
        except Exception:
            return None

    @staticmethod
    def _states(element):
        names = []
        for flag in _STATE_FLAGS:
            try:
                if bool(getattr(element, "Current" + flag)):
                    names.append(flag)
            except Exception:
                continue
        names.extend(_pattern_states(element))
        return tuple(names)
