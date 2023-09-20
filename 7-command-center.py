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
S_FAULT = "FAULT"
S_CLEARFAULT = "CLEAR"
        

async def publish_message(serial, client, app, action, name, value):
    print(f"{time.ctime()} - PUBLISH [{serial}] {name}:{value}")
    await asyncio.sleep(2)
    payload = {
                "action"    : "get",
                "project"   : student_id,
                "model"     : "model-01",
                "serial"    : serial,
                "name"      : name,
                "value"     : value
            }
    print(f"{time.ctime()} - PUBLISH - [{serial}] - {payload['name']} > {payload['value']}")
    await client.publish(f"v1cdti/{app}/{action}/{student_id}/model-01/{serial}"
                        , payload=json.dumps(payload))

async def monitor(client):
    while True:
        await asyncio.sleep(10)
        payload = {
                    "action"    : "get",
                    "project"   : student_id,
                    "model"     : "model-01",

                }
        print(f"{time.ctime()} - PUBLISH - GET ALL MACHINE STATUS")
        await client.publish(f"v1cdti/app/get/{student_id}/model-01/"
                            , payload=json.dumps(payload))

async def listen(client):
    async with client.messages() as messages:
        print(f'{time.ctime()}  subscribe for topic v1cdti/hw/get/{student_id}/model-01/')
        print(f'{time.ctime()}  subscribe for topic v1cdti/app/get/{student_id}/model-01/')
        await client.subscribe(f"v1cdti/hw/get/{student_id}/model-01/+")
        async for message in messages:
            mgs_decode = json.loads(message.payload)
            # print(mgs_decode)
            if message.topic.matches(f"v1cdti/hw/get/{student_id}/model-01/+"):
                print(f"{time.ctime()} FROM MQTT: [{mgs_decode['serial']} {mgs_decode['name']} {mgs_decode['value']}]")

                if (mgs_decode['name'] == S_FAULT):
                    await publish_message(mgs_decode['serial'], client, 'hw', 'set', "STATUS", S_CLEARFAULT)
                
                if (mgs_decode['name'] == "STATUS" and mgs_decode['value']==S_OFF):
                    await publish_message(mgs_decode['serial'], client, 'hw', 'set', "STATUS", S_READY)
                
                if (mgs_decode['name'] == "STATUS" and mgs_decode['value']==S_FILLING):
                    await asyncio.sleep(2)
                    await publish_message(mgs_decode['serial'], client, 'hw', 'set', "WATERLEVEL", S_FULLLEVEL)
                
                if (mgs_decode['name'] == "STATUS" and mgs_decode['value']==S_HEATING):
                    await asyncio.sleep(2)
                    await publish_message(mgs_decode['serial'], client, 'hw', 'set', "TEMPERATURE", S_TEMPERATURE)
                      
                
async def main():
    async with aiomqtt.Client("test.mosquitto.org") as client:
       await asyncio.gather(listen(client), monitor(client))
    
    


# Change to the "Selector" event loop if platform is Windows
if sys.platform.lower() == "win32" or os.name.lower() == "nt":
    from asyncio import set_event_loop_policy, WindowsSelectorEventLoopPolicy
    set_event_loop_policy(WindowsSelectorEventLoopPolicy())
# Run your async application as usual
asyncio.run(main())