import asyncio
import time
async def waiter(event):
    print(f'{time.ctime()} waiting for it ...')
    await event.wait()
    print(f'{time.ctime()}... got it!')

async def main():
    # Create an Event object.
    event = asyncio.Event()

    # Spawn a Task to wait until 'event' is set.
    waiter_task = asyncio.create_task(waiter(event))

    # Sleep for 1 second and set the event.
    await asyncio.sleep(5)

    event.set()

    # Wait until the waiter task is finished.
    await waiter_task

asyncio.run(main())