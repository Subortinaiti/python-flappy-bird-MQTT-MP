import pygame as pg
import paho.mqtt.client as mqtt
import random,string,math,time,threading,queue,json
pg.init()

SCALE = 1
SETTINGS_FILE = "data/shared_settings.json"
I_AM_YOUR_ONLY_GOD_BOW_BEFORE_ME = False
autoplay = False

# Function to load settings from JSON file
def load_settings():
    with open(SETTINGS_FILE) as f:
        return json.load(f)

def render_text(text, font, color, x, y, display):
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect()
    text_rect.topleft = (x, y)
    display.blit(text_surface, text_rect)


# Load settings from JSON file
settings = load_settings()

BACKGROUND_SCROLLSPEED = settings["BACKGROUND_SCROLLSPEED"]
PIPE_SCROLLSPEED = settings["PIPE_SCROLLSPEED"]
GRAVITY = settings["GRAVITY"]
CLOCKSPEED = settings["CLOCKSPEED"]
JUMPFORCE = settings["JUMPFORCE"]
PIPEMARGIN = settings["PIPEMARGIN"]
GAPSIZE = settings["GAPSIZE"]
WHOOSH = settings["WHOOSH"]
MQTT_PIPES_TOPIC = settings["MQTT_PIPES_TOPIC"]
MQTT_PLAYERDATA_TOPIC = settings["MQTT_PLAYERDATA_TOPIC"]
MQTT_DEATHANNOUNCEMENT_TOPIC = settings["MQTT_DEATHANNOUNCEMENT_TOPIC"]
MQTT_PIPEPASS_TOPIC = settings["MQTT_PIPEPASS_TOPIC"]

"""
background.png 1920x640
bird.png 75x60
pipe_bottom.png 90x960
pipe_top.png 90x960
coin.png 48x48
"""

BACKGROUND_IMG = pg.transform.scale(pg.image.load("images/background.png"), (1920 * SCALE, 640 * SCALE))
BIRD_IMG = pg.transform.scale(pg.image.load("images/bird.png"), (75 * SCALE, 60 * SCALE))
EVILBIRD_IMG = pg.transform.scale(pg.image.load("images/evilbird.png"), (75 * SCALE, 60 * SCALE))
PIPEBOTTOM_IMG = pg.transform.scale(pg.image.load("images/pipe_bottom.png"), (90 * SCALE, 960 * SCALE))
PIPETOP_IMG = pg.transform.scale(pg.image.load("images/pipe_top.png"), (90 * SCALE, 960 * SCALE))
#COIN_IMG = pg.transform.scale(pg.image.load("images/coin.png"), (48 * SCALE, 48 * SCALE))

BLACK_CLR = (0,0,0)





class Bird:
    def __init__(self,username,image=BIRD_IMG):
        self.unscaled_x,self.unscaled_y = 32,320
        self.image = image
        self.name = username
        self.vel = 0


    def draw_self(self,display,font,show_tag=False):

#        display.blit(self.image,(self.unscaled_x*SCALE,self.unscaled_y*SCALE))
        
        rotated_image = pg.transform.rotate(self.image, -self.vel * 3)  # Rotate the image based on velocity
        rotated_rect = rotated_image.get_rect(center=(self.unscaled_x * SCALE + rotated_image.get_width() / 2,
                                                       self.unscaled_y * SCALE + rotated_image.get_height() / 2))
        display.blit(rotated_image, rotated_rect.topleft)

        if show_tag:
            drawy = (self.unscaled_y-10)*SCALE
            text_surface = font.render(self.name, False, BLACK_CLR)
            text_rect = text_surface.get_rect(center=((self.unscaled_x + 37.5) * SCALE, drawy))
            display.blit(text_surface, text_rect)
        

    def calculate_self(self):
        self.vel += GRAVITY
        self.unscaled_y += self.vel

        if self.unscaled_y*SCALE >= 640*SCALE and WHOOSH:
            self.unscaled_y = -75 * SCALE
            self.vel /= 2
            
        

    def jump(self):
        self.vel = -JUMPFORCE

def drawpipe(x,y,display,imagetop=PIPETOP_IMG,imagebottom=PIPEBOTTOM_IMG):
    top_y = (-960+y)*SCALE
    bottom_y = (y+GAPSIZE)*SCALE

    display.blit(imagetop,(x*SCALE,top_y))
    display.blit(imagebottom,(x*SCALE,bottom_y))    


####################################################################################################################################

def on_message(client, userdata, msg):
    global pipes,score
    if msg.topic != MQTT_PIPEPASS_TOPIC:
        pipes = eval(msg.payload.decode("utf-8"))
    else:
        score += 1

def on_playerdisconnectmessage(client,userdata,msg):
    global otherbirds,dead
    
    name = msg.payload.decode("utf-8")
    print("disconnect packet recieved:",name)
    if name == username and not I_AM_YOUR_ONLY_GOD_BOW_BEFORE_ME:
        dead = True
        
    for bird in otherbirds:
        if bird.name == name:
            otherbirds.pop(otherbirds.index(bird))
            print("A bird has been disconnected:",name)
            return
    

def on_playerdatamessage(client,userdata,msg):
    global otherbirds
    data = eval(msg.payload)
    name,x,y= data["bird data"]["username"],data["bird data"]["x"],data["bird data"]["y"]
    try:
        vel = data["bird data"]["vel"]
    except:
        print(data)

    if name == username:
        return
    if not otherbirds:
        otherbirds.append(Bird(name,image=EVILBIRD_IMG))
        otherbirds[0].unscaled_x = x
        otherbirds[0].unscaled_y = y
        otherbirds[0].vel = vel
        print("new bird connected")
    for bird in otherbirds:
        if name == bird.name:
            bird.unscaled_x = x
            bird.unscaled_y = y
            bird.vel = vel
            return
        
    otherbirds.append(Bird(name,image=EVILBIRD_IMG))
    otherbirds[-1].unscaled_x = x
    otherbirds[-1].unscaled_y = y
    otherbirds[0].vel = vel
    print("new bird has connected")       




####################################################################################################################################

def startmenu(display, font, displaysize):
    started = False
    username = ""
    server_host = ""
    input_username = True

    while not started:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                pg.quit()
                quit()

            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    started = True
                    pg.quit()
                    quit()
                
                if input_username:
                    if event.key == pg.K_RETURN:
                        if len(username) >= 4:
                            input_username = False
                    elif event.key == pg.K_BACKSPACE:
                        username = username[:-1]
                    elif event.unicode in string.printable:
                        if len(username) <= 12:
                            username += event.unicode
                else:
                    if event.key == pg.K_RETURN:
                        if len(server_host) >= 4:
                            started = True
                            break
                    elif event.key == pg.K_BACKSPACE:
                        server_host = server_host[:-1]
                    elif event.unicode in string.printable:
                        if len(server_host) <= 255:
                            server_host += event.unicode

        display.blit(BACKGROUND_IMG, (0, 0))
        
        if input_username:
            input_text = "Enter username, ENTER to continue:"
            input_render = font.render(input_text, True, (0, 0, 0))
            display.blit(input_render, (displaysize[0]/2 - input_render.get_width()/2, displaysize[1]/2 - input_render.get_height()))
            input_render = font.render(username, True, (0, 0, 0))
            display.blit(input_render, (displaysize[0]/2 - input_render.get_width()/2, displaysize[1]/2))
        else:
            input_text = "Enter server host, ENTER to begin:"
            input_render = font.render(input_text, True, (0, 0, 0))
            display.blit(input_render, (displaysize[0]/2 - input_render.get_width()/2, displaysize[1]/2 - input_render.get_height()))
            input_render = font.render(server_host, True, (0, 0, 0))
            display.blit(input_render, (displaysize[0]/2 - input_render.get_width()/2, displaysize[1]/2))

        pg.display.flip()

    return username, server_host


def main():
    global pipes,otherbirds,username,dead,score,I_AM_YOUR_ONLY_GOD_BOW_BEFORE_ME,autoplay
    displaysize = (960*SCALE,640*SCALE)
    fontA = pg.font.Font("data/MinecraftRegular-Bmg3.otf",int(45*SCALE))
    fontB = pg.font.Font("data/MinecraftRegular-Bmg3.otf",int(20*SCALE))

    clock = pg.time.Clock()
    display = pg.display.set_mode(displaysize)
    pg.display.set_caption("Flappi berd: multipleier")
    score = 0
    pipes = []
#    mqtthost = "localhost"
    username,mqtthost = startmenu(display,fontA,displaysize)

    otherbirds = []

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_message = on_message
    client.connect(mqtthost, 1883, 60)
    client.subscribe(MQTT_PIPES_TOPIC)
    client.subscribe(MQTT_PIPEPASS_TOPIC)
    client.loop_start()

    transclient = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    transclient.connect(mqtthost, 1883, 60)
    transclient.subscribe(MQTT_PLAYERDATA_TOPIC)
    transclient.on_message = on_playerdatamessage
    transclient.loop_start()
    
    disclient = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    disclient.connect(mqtthost, 1883, 60)
    disclient.subscribe(MQTT_DEATHANNOUNCEMENT_TOPIC)
    disclient.on_message = on_playerdisconnectmessage
    disclient.loop_start()


    bird = Bird(username)

    background_offset = 0


    
    print("welcome,",username+"!")
    
    dead = False
    while not dead:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                dead = True
            elif event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    dead = True

                elif event.key in [pg.K_SPACE,pg.K_UP,pg.K_w]:
                    bird.jump()




                
                elif event.key == pg.K_g:
                    I_AM_YOUR_ONLY_GOD_BOW_BEFORE_ME = not I_AM_YOUR_ONLY_GOD_BOW_BEFORE_ME
                elif event.key == pg.K_k:
                    autoplay = not autoplay



        # Autoplay logic
        if autoplay:
            if pipes:
                nearest_pipe = None
                nearest_distance = float('inf')
                for pipe_x, pipe_y in pipes:
                    distance = pipe_x - bird.unscaled_x
                    if -90 < distance < nearest_distance:
                        nearest_pipe = (pipe_x, pipe_y)
                        nearest_distance = distance

                if nearest_pipe:
                    pipe_x, pipe_y = nearest_pipe
                    gap_center = pipe_y + GAPSIZE / 2
                    # If the bird is below the gap center, jump to align
                    if bird.unscaled_y > gap_center - 20:
                        bird.jump()

        # logic

        if background_offset > -displaysize[0]:
            background_offset -= BACKGROUND_SCROLLSPEED*SCALE
        else:
           background_offset = 0
 
        
        bird.calculate_self()

        information = {
            "bird data": {
                "username":username,
                "x":bird.unscaled_x,
                "y":bird.unscaled_y,
                "vel":bird.vel
                }

            }
        
        transclient.publish(MQTT_PLAYERDATA_TOPIC, str(information))
        
        # rendering
        display.fill(BLACK_CLR)
        display.blit(BACKGROUND_IMG, (int(background_offset*SCALE), 0))
        

        for b in otherbirds:
            b.draw_self(display,fontB,show_tag=True)

        for p in pipes:
            p[0] -= PIPE_SCROLLSPEED

        for x,y in pipes:
            
            drawpipe(x,y,display)



        bird.draw_self(display,fontB)
        
        if not I_AM_YOUR_ONLY_GOD_BOW_BEFORE_ME:
            score_text = f"Score: {score}"
        else:
            score_text = f"Score: {score}."
        text_width, text_height = fontA.size(score_text)
        render_text(score_text, fontA, (255, 255, 255), displaysize[0] - text_width - 10, 10, display)
        
        pg.display.flip()
        clock.tick(CLOCKSPEED)









####################################################################################################################################

if __name__ == "__main__":
    runnerthread = threading.Thread(target=main,daemon=True)
    runnerthread.start()

    runnerthread.join()

    pg.quit()
    quit()
