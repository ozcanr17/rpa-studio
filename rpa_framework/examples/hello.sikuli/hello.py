print("Hello from a .sikuli bundle running on RPA Framework")
print("This folder is my image search path:", getBundlePath())
Settings.MinSimilarity = 0.8
emit("stage", "starting")

try:
    target = exists("logo.png", 3)
    if target:
        print("found logo at", target.getTarget())
        hover(target)
        passed("logo located")
    else:
        print("logo.png present but not on screen right now")
        passed("demo finished")
except FindFailed:
    print("no logo.png in this bundle yet - drop one in to try image search")
    passed("demo finished without an image target")
