print("move your mouse onto any button or field...")
for remaining in (3, 2, 1):
    print(remaining, "...")
    sleep(1.0)
backend = OSFacadeFactory.create()
inspector = InspectorFactory.create()
x, y = backend.cursor_position()
element = inspector.element_at(x, y)
print(element.to_json() if element else "nothing recognized at cursor")
