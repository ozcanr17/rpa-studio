IMAGE: my_button.png

try:
    target = exists("my_button.png", 5)
    if target:
        print("found it at", target.getTarget(), "score", round(target.getScore(), 2))
        hover(target)
        popup("Found my_button.png on your screen")
    else:
        print("my_button.png exists but is not visible on screen right now")
except FindFailed:
    print("my_button.png does not exist next to this script yet")
    print("crop a small screenshot, save it as my_button.png beside this file, and run again")
