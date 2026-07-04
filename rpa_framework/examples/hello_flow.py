import asyncio


async def main():
    print("Hello! I am your automation robot.")
    for step in range(1, 4):
        emit("progress", {"step": step, "of": 3})
        print("doing step", step, "of 3")
        await checkpoint()
        await asyncio.sleep(0.7)
    print("done - press Run to watch me again")
