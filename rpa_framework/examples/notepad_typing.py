app = openApp("notepad.exe")
if app and app.focus():
    sleep(0.5)
    app.window().moveTo(80, 80).resize(900, 600)
    type("Hello from RPA Studio!" + Key.ENTER)
    type("A robot typed this line." + Key.ENTER)
    emit("notepad", "typing finished")
    passed("typed two lines into Notepad")
else:
    failed("could not find the Notepad window")
