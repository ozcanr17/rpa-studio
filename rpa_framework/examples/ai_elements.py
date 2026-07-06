regions = findUI("any")
print("AI vision found {} interactable elements".format(len(regions)))
for region in regions[:10]:
    print("  ", region)

ok_buttons = findUI("button", text="OK")
if ok_buttons:
    print("an OK element is at", ok_buttons[0].getCenter())
    ok_buttons[0].highlight(1)
else:
    print("no OK element on screen right now")
