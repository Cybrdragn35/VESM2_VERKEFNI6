from mqtt_as import MQTTClient, config
from machine import Pin, SoftI2C
from I2C_LCD import I2cLcd
import asyncio
from lib.dfplayer import DFPlayer

config["ssid"] = "TskoliVESM"
config["wifi_pw"] = "Fallegurhestur"

config["server"] = "10.201.48.166"
config["queue_len"] = 1

TOPIC = "0311kynning"
TOPIC_2 = "2007kynning"
TOPIC_3 = "1234kynning"
TOPIC_4 = "5678kynning"

df = DFPlayer(2)
df.init(tx=17, rx=16)

i2c = SoftI2C(scl=Pin(13), sda=Pin(10), freq=400000)
lcd = I2cLcd(i2c, 39, 2, 16)


startCount = False
curPlayer = ""
counter = 0

pl1_blinks = 0
pl2_blinks = 0

def updateScreen(text1, text2):
    lcd.clear()
    lcd.move_to(0, 0)
    lcd.putstr(text1)
    lcd.move_to(0, 1)
    lcd.putstr(text2)

async def mottakari(client):
    global counter
    async for topic, skilabod, _ in client.queue:
        tala = skilabod.decode()
        counter = int(tala)
        print(f"blikk: {counter}")

async def sendir(client):
    while True:
        skilabod = str(startCount).encode()
        skilabod2 = curPlayer.encode()
        skilabod3 = f"{pl1_blinks} {pl2_blinks}".encode() 
        await client.publish(TOPIC_2, skilabod)
        await client.publish(TOPIC_3, skilabod2)
        await client.publish(TOPIC_4, skilabod3)
        await asyncio.sleep_ms(1000)

async def askrift(client):
    while True:
        await client.up.wait()
        client.up.clear()
        await client.subscribe(TOPIC, 1) 
        
        
async def game():
    global startCount
    global curPlayer
    global counter
    global pl1_blinks
    global pl2_blinks
    
    print("WELCOME TO THE GAME!!")
    updateScreen("WELCOME TO", "THE GAME!")
    await asyncio.sleep(5)
    for i in range(5, 0, -1):
        updateScreen("PLAYER 1 START", f"STARTS IN {i}")
        await asyncio.sleep(0.5)
        updateScreen("LOOK CAMERA", f"STARTS IN {i}")
        await asyncio.sleep(0.5)
    print("PLAYER 1 START!")
    curPlayer = "pl1"
    startCount = True
    await df.play(1, 1) # horn
    for i in range(10, 0, -1):
        updateScreen("BLINK ASAP!!", f"ENDS IN: {i}")
        await asyncio.sleep(1)
    startCount = False
    await df.play(1, 1) # horn
    updateScreen("PL1 BLINKED", f"{counter} times")
    pl1_blinks = counter
    await asyncio.sleep(10)
    counter = 0
    
    # player 2 time!
    
    for i in range(5, 0, -1):
        updateScreen("PLAYER 2 START", f"STARTS IN {i}")
        await asyncio.sleep(0.5)
        updateScreen("LOOK CAMERA", f"STARTS IN {i}")
        await asyncio.sleep(0.5)
    print("PLAYER 2 START!")
    await df.play(1, 1) # horn
    curPlayer = "pl2"
    startCount = True
    for i in range(10, 0, -1):
        updateScreen("BLINK ASAP!!", f"ENDS IN: {i}")
        await asyncio.sleep(1)
    startCount = False
    await df.play(1, 1) # horn
    updateScreen("PL2 BLINKED", f"{counter} times")
    pl2_blinks = counter
    await asyncio.sleep(10)
    counter = 0
    
    
    # end!
    
    updateScreen(f"PL1 SCORE: {pl1_blinks}", f"PL2 SCORE: {pl2_blinks}")
    await asyncio.sleep(5)
    
    if pl1_blinks > pl2_blinks:
        updateScreen("PLAYER 1 WINS!!", "")
        await df.play(3, 3)
    elif pl2_blinks > pl1_blinks:
        updateScreen("PLAYER 2 WINS!!", "")
        await df.play(3, 3)
    else:
        updateScreen("ITS A TIE...", "")
        await df.play(2, 2)
    await asyncio.sleep(3)
    
async def main(client):
    updateScreen("CONNECTING...", "Please wait!")
    await client.connect()
    asyncio.create_task(askrift(client))
    asyncio.create_task(mottakari(client))
    asyncio.create_task(sendir(client))
    
    while True:
        await game()
        await asyncio.sleep_ms(0)
  
MQTTClient.DEBUG = True

client = MQTTClient(config)

try:
    asyncio.run(main(client))
finally:
    client.close()

