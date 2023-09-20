import time
import random
import json
import asyncio
import aiomqtt
from enum import Enum
import sys
import os

student_id = "6310301021"
S_OFF = "OFF"
S_READY = "READY"
S_LID = "CLOSE"
S_FILLING = "FILLING"
S_FULLLEVEL = "FULL"
S_HEATING = "HEATING"
S_TEMPERATURE = "REACH"
S_RINSE = "RINSE"
S_SPIN = "SPIN"
S_WASH = "WASH"

class MachineStatus():
    def __init__(self) -> None:
        self.fulldetect = 0
        self.heatreach = 1
    #
    # add more machine status
    # 

class MachineMaintStatus():
    def __init__(self) -> None:
        self.filter = random.choice(["clear", "clogged"])
        self.noise = random.choice(["quiet", "noisy"])
    #
    # add more maintenance status
    #

class WashingMachine:
    def __init__(self, serial):
        self.MACHINE_STATUS = 'OFF'
        self.SERIAL = serial
        self.task = None
        # self.event = asyncio.Event()

async def wait_event(event):
    print(f'{time.ctime()} Waiting for event ...')
    await event.wait()
    print(f'{time.ctime()} Get new information! ')

async def waiting(w, next_status, status_type):
    try:
        print(f'{time.ctime()} - Start waiting')
        await asyncio.sleep(30)
        print(f'{time.ctime()} - Waiting 10 second already! -> TIMEOUT!')
        w.MACHINE_STATUS = next_status
        w.FAULT_TYPE = status_type
        print(f'{time.ctime()} - [{w.SERIAL}] STATUS: {w.MACHINE_STATUS}')
    except asyncio.CancelledError:
        print(f'{time.ctime()} - Waiting function is canceled!')
        


async def cancel_waiting(task):
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print(f'{time.ctime()} - Get message before timeout!')
        

async def publish_message(w, client, app, action, name, value):
    print(f"{time.ctime()} - [{w.SERIAL}] {name}:{value}")
    await asyncio.sleep(2)
    payload = {
                "action"    : "get",
                "project"   : student_id,
                "model"     : "model-01",
                "serial"    : w.SERIAL,
                "name"      : name,
                "value"     : value
            }
    print(f"{time.ctime()} - PUBLISH - [{w.SERIAL}] - {payload['name']} > {payload['value']}")
    await client.publish(f"v1cdti/{app}/{action}/{student_id}/model-01/{w.SERIAL}"
                        , payload=json.dumps(payload))


async def CoroWashingMachine(w, client):
    # washing coroutine
    while True:
        # wait_next = round(10*random.random(),2)
        # print(f"{time.ctime()} - [{w.SERIAL}] Waiting new message... {wait_next} seconds.")
        # await asyncio.sleep(wait_next)
        print(f'{time.ctime()} - {w.SERIAL} waiting')
        w.event = asyncio.Event()
        if w.MACHINE_STATUS == 'OFF':
            # continue
            await publish_message(w, client, 'hw', 'get', 'STATUS', w.MACHINE_STATUS)
            waiter_task = asyncio.create_task(wait_event(w.event))
            await waiter_task
    
        if w.MACHINE_STATUS == 'READY':
            print(f"{time.ctime()} - [{w.SERIAL}-{w.MACHINE_STATUS}]")
            await publish_message(w, client, 'hw', 'get', 'STATUS', 'READY')

            await publish_message(w, client, 'hw', 'get', 'LID', 'CLOSE')

            w.MACHINE_STATUS = 'FILLING'
            await publish_message(w, client, 'hw', 'get', 'STATUS', 'FILLING')
            w.task = asyncio.create_task(waiting(w, 'FAULT', 'TIMEOUT'))
            await w.task

        if w.MACHINE_STATUS == 'FAULT':
            await publish_message(w, client, 'hw', 'get', 'FAULT', w.FAULT_TYPE)
            
            print(f"{time.ctime()} - [{w.SERIAL}] Waiting to clear fault...")
            waiter_task = asyncio.create_task(wait_event(w.event))
            await waiter_task

        if w.MACHINE_STATUS == 'HEATING':
            w.task = asyncio.create_task(waiting(w, 'FAULT', 'TIMEOUT'))
            await w.task
 
        if w.MACHINE_STATUS == 'WASH':
            w.task = asyncio.create_task(waiting(w, 'RINSE', ''))
            await w.task

        if w.MACHINE_STATUS == 'RINSE':
            await publish_message(w, client, 'hw', 'get', 'STATUS', 'RINSE')
            w.task = asyncio.create_task(waiting(w, 'SPIN', ''))
            await w.task

        if w.MACHINE_STATUS == 'SPIN':
            await publish_message(w, client, 'hw', 'get', 'STATUS', 'SPIN')
            w.task = asyncio.create_task(waiting(w, 'OFF', ''))
            await w.task


async def listen(w, client):
    async with client.messages() as messages:
        print(f'{time.ctime()} {w.SERIAL} subscribe for topic v1cdti/hw/set/{student_id}/model-01/{w.SERIAL}')
        await client.subscribe(f"v1cdti/hw/set/{student_id}/model-01/{w.SERIAL}")
        await client.subscribe(f"v1cdti/app/get/{student_id}/model-01/")
        async for message in messages:
            mgs_decode = json.loads(message.payload)
            # print(mgs_decode)
            if message.topic.matches(f"v1cdti/hw/set/{student_id}/model-01/{w.SERIAL}"):
                print(f"{time.ctime()} - FROM MQTT: [{mgs_decode['serial']} {mgs_decode['name']} {mgs_decode['value']}]")

                if (mgs_decode['name'] == "STATUS"):
                    w.MACHINE_STATUS = mgs_decode['value']
                    w.event.set()

                if w.MACHINE_STATUS == 'FILLING':
                    if mgs_decode['name'] == "WATERLEVEL":
                        if mgs_decode['value'] == 'FULL':
                            w.MACHINE_STATUS = 'HEATING'
                            print(f'{time.ctime()} - [{w.SERIAL}] STATUS: {w.MACHINE_STATUS}')
                            await publish_message(w, client, 'hw', 'get', 'STATUS', w.MACHINE_STATUS)
                            await cancel_waiting(w.task)

                if w.MACHINE_STATUS == 'HEATING':
                    if mgs_decode['name'] == "TEMPERATURE":
                        if mgs_decode['value'] == 'REACH':
                            w.MACHINE_STATUS = 'WASH'
                            print(f'{time.ctime()} - [{w.SERIAL}] STATUS: {w.MACHINE_STATUS}')
                            await publish_message(w, client, 'hw', 'get', 'STATUS', w.MACHINE_STATUS)

                        await cancel_waiting(w.task)

                if w.MACHINE_STATUS == 'WASH':
                    if mgs_decode['name'] == "FAULT":
                        w.MACHINE_STATUS = 'FAULT'
                        w.FAULT_TYPE = 'IMBALANCE'
                        await publish_message(w, client, 'hw', 'get', 'STATUS', w.MACHINE_STATUS)
                        await cancel_waiting(w.task)
                
                if w.MACHINE_STATUS == 'RINSE':
                    if mgs_decode['name'] == "FAULT":
                        w.MACHINE_STATUS = 'FAULT'
                        w.FAULT_TYPE = 'MOTORFAILED'
                        await publish_message(w, client, 'hw', 'get', 'STATUS', w.MACHINE_STATUS)
                        await cancel_waiting(w.task)
                
                if w.MACHINE_STATUS == 'SPIN':
                    if mgs_decode['name'] == "FAULT":
                        w.MACHINE_STATUS = 'FAULT'
                        w.FAULT_TYPE = 'MOTORFAILED'
                        await publish_message(w, client, 'hw', 'get', 'STATUS', w.MACHINE_STATUS)
                        await cancel_waiting(w.task)

                if mgs_decode['name'] == "FAULT":
                    if mgs_decode['value'] == 'CLEAR':
                        w.MACHINE_STATUS = 'OFF'
                        await publish_message(w, client, 'hw', 'get', 'STATUS', w.MACHINE_STATUS)

            if message.topic.matches(f"v1cdti/app/get/{student_id}/model-01/"):
                print(f'{time.ctime()} - get monitor request')
                await publish_message(w, client, 'app', 'monitor', 'STATUS', w.MACHINE_STATUS)                        
                

async def main():
    n = 2
    ws = [WashingMachine(serial=f'SN-00{i}') for i in range(n)]
    

    async with aiomqtt.Client("test.mosquitto.org") as client:
    # async with aiomqtt.Client("broker.hivemq.com") as client:
        listeners = [listen(w, client) for w in ws]
        washer = [CoroWashingMachine(w, client) for w in ws]
        await asyncio.gather(*listeners, *washer)
    
    


# Change to the "Selector" event loop if platform is Windows
if sys.platform.lower() == "win32" or os.name.lower() == "nt":
    from asyncio import set_event_loop_policy, WindowsSelectorEventLoopPolicy
    set_event_loop_policy(WindowsSelectorEventLoopPolicy())
# Run your async application as usual
asyncio.run(main())