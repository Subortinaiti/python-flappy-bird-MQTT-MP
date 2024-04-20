import paho.mqtt.client as mqtt
import time,random,threading,json,logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()


MQTT_HOST = "localhost"
MQTT_HOST = input("type the broker host (if the broker is running on this machine, type localhost) > ")
MQTT_PORT = 1883

SETTINGS_FILE = "data/shared_settings.json"

# Function to load settings from JSON file
def load_settings():
    with open(SETTINGS_FILE) as f:
        return json.load(f)

# Load settings from JSON file
settings = load_settings()



MQTT_TOPIC = settings["MQTT_PIPES_TOPIC"]
PIPEMARGIN = settings["PIPEMARGIN"]
GAPSIZE = settings["GAPSIZE"]
PIPE_SCROLLSPEED = settings["PIPE_SCROLLSPEED"]
MQTT_PLAYERDATA_TOPIC = settings["MQTT_PLAYERDATA_TOPIC"]
MQTT_DEATHANNOUNCEMENT_TOPIC = settings["MQTT_DEATHANNOUNCEMENT_TOPIC"]
MQTT_PIPEPASS_TOPIC = settings["MQTT_PIPEPASS_TOPIC"]
GENERATION_DELAY = settings["GENERATION_DELAY"]

BIRDW,BIRDH = 75,60

birdinfo = {}


def is_colliding(rect1, rect2):

    x1, y1, w1, h1 = rect1
    x2, y2, w2, h2 = rect2

    if x1 + w1 < x2 or x2 + w2 < x1:
        return False
    if y1 + h1 < y2 or y2 + h2 < y1:
        return False
    return True

def getBirdDeaths():
    global birdinfo

    birds_to_remove = []
    for name,data in birdinfo.items():
        if data["immunityTimer"] <= 0:
            x,y,vel = data["x"],data["y"],data["vel"]
            birdrect = [x,y,75,60]
            for pipe in pipes:
                piperect = pipe[0],pipe[1]-960,90,960
                if is_colliding(birdrect,piperect):
#                    logger.debug(name,"has collided with the top pipe!")
                    birds_to_remove.append(name)
                    continue
                piperect = pipe[0],pipe[1]+GAPSIZE,90,960
                if is_colliding(birdrect,piperect):
#                    logger.debug(name,"has collided with the bottom pipe!")
                    birds_to_remove.append(name)
                    continue

    return birds_to_remove

def generate_pipe():
    global pipes
    pipe_y = random.randint(PIPEMARGIN,640-PIPEMARGIN-GAPSIZE)
    pipe_x = 970
    pipes.append([pipe_x,pipe_y])
    logger.debug(f"Pipe added ({pipe_y})")

def add_pipes():
    global pipes
    while True:
        generate_pipe()
        time.sleep(GENERATION_DELAY)


def on_message(client, userdata, msg):
    global birdinfo
    data = eval(msg.payload)
    name,x,y = data["bird data"]["username"],data["bird data"]["x"],data["bird data"]["y"]
    vel = data["bird data"]["vel"]

    if name in birdinfo.keys():
        birdinfo[name] = {
            "x":x,
            "y":y,
            "vel":vel,
            "disconnectTimer":time.time(),
            "immunityTimer": birdinfo[name]["immunityTimer"] -1
            }
    else:
        birdinfo[name] = {
            "x":x,
            "y":y,
            "vel":vel,
            "disconnectTimer":time.time(),
            "immunityTimer": 500
            }        
        


def tickpipes(client):
    global pipes
    for pipe in pipes:
        try:
            pipe[0] -= PIPE_SCROLLSPEED

            if pipe[0] <= -90:
                pipes.pop(pipes.index(pipe))
                client.publish(MQTT_PIPEPASS_TOPIC,"ehe")
                logger.debug("pipe got zapped")            
        except:
            logger.debug("errore pazzurdopazzo")
        

def main():
    global pipes, birdinfo
    pipes = []
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(MQTT_HOST, MQTT_PORT, 60)

    dataclient = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    dataclient.connect(MQTT_HOST, MQTT_PORT, 60)
    dataclient.on_message = on_message
    dataclient.subscribe(settings["MQTT_PLAYERDATA_TOPIC"])

    client.loop_start()
    dataclient.loop_start()

    logger.debug("successful!")

    pipegenthread = threading.Thread(target=add_pipes, daemon=True)
    pipegenthread.start()

    while True:
        start_time = time.time()
        tickpipes(client)
        client.publish(MQTT_TOPIC, str(pipes))

        currentTime = time.time()
        birds_to_remove = []  # List to store keys to remove
        for name, data in birdinfo.items():
            lastpacket = data["disconnectTimer"]
            if currentTime - lastpacket > 5:
                logger.debug(f"WARNING: the bird {name} has stopped responding.")
                birds_to_remove.append(name)  # Add key to remove
                

        birds_to_remove.extend(getBirdDeaths())
        # Remove keys from birdinfo
        for name in birds_to_remove:
            client.publish(MQTT_DEATHANNOUNCEMENT_TOPIC, name)
            del birdinfo[name]
            

        
        
        loop_execution_time = time.time() - start_time
        desired_delay = 1 / 100 - loop_execution_time
        if desired_delay > 0:
            time.sleep(desired_delay)
        else:
            logger.debug(f"Warning: Execution time exceeded desired frequency. is the server overloaded? ({-round(desired_delay, 4)}s).")

if __name__ == "__main__":
    threadrunner = threading.Thread(target=main,daemon=True)
    threadrunner.start()

    threadrunner.join()







