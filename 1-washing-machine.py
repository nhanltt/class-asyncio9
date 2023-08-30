import time
import random
import json
import asyncio
import aiomqtt
from enum import Enum
import sys
import os

student_id = "6310301021"

class MachineStatus():
    def __init__(self) -> None:
        self.pressure = round(random.uniform(2000,3000), 2)
        self.temperature = round(random.uniform(25.0,40.0), 2)
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
        wait_next = round(10*random.random(),2)
        print(f"{time.ctime()} - [{w.SERIAL}] Waiting to start... {wait_next} seconds.")
        await asyncio.sleep(wait_next)
        if w.MACHINE_STATUS == 'ON':
            await publish_message(w, client, 'hw', 'get', 'STATUS', 'START')
            await publish_message(w, client, 'hw', 'get', 'LID', 'OPEN')
            await publish_message(w, client, 'hw', 'get', 'LID', 'CLOSE')

            mc_status = MachineStatus()
            # press = random.choice([MachineStatus.pressure])
            # temp = random.choice([MachineStatus.temperature])
            press = mc_status.pressure
            temp = mc_status.temperature
            
            await publish_message(w, client, 'hw', 'get', 'pressure', str(press))
            await publish_message(w, client, 'hw', 'get', 'tempurature', str(temp))

            filter_check = MachineMaintStatus().filter
            noise_check = MachineMaintStatus().noise

            await publish_message(w, client, 'hw', 'get', 'filter', filter_check)
            await publish_message(w, client, 'hw', 'get', 'noise', noise_check)

            await publish_message(w, client, 'hw', 'get', 'STATUS', 'FINISH')

            if noise_check == 'noisy':
                w.MACHINE_STATUS = 'OFF'
                continue
        else:
            continue

        

async def listen(w, client):
    async with client.messages() as messages:
        await client.subscribe(f"v1cdti/hw/set/{student_id}/model-01/{w.SERIAL}")
        async for message in messages:
            mgs_decode = json.loads(message.payload)
            if message.topic.matches(f"v1cdti/hw/set/{student_id}/model-01/{w.SERIAL}"):
                print(f"FROM MQTT: [{mgs_decode['serial']} {mgs_decode['name']} {mgs_decode['value']}]")
                w.MACHINE_STATUS = 'ON'
        


async def main():
    w = WashingMachine(serial='SN-001')
    # async with aiomqtt.Client("test.mosquitto.org") as client:
    async with aiomqtt.Client("broker.hivemq.com") as client:
       await asyncio.gather(listen(w, client), CoroWashingMachine(w, client))
    


# Change to the "Selector" event loop if platform is Windows
if sys.platform.lower() == "win32" or os.name.lower() == "nt":
    from asyncio import set_event_loop_policy, WindowsSelectorEventLoopPolicy
    set_event_loop_policy(WindowsSelectorEventLoopPolicy())
# Run your async application as usual
asyncio.run(main())