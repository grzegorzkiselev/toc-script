from telethon import TelegramClient, sync
import configparser
import time

config = configparser.ConfigParser()
config.read("./conf.ini")

# Put your api_id, api_hash and channel url into "conf.ini" file it the same folder
API_ID = config['Telegram']['API_ID']
API_HASH = config['Telegram']['API_HASH']
CHANNEL = config['Telegram']['CHANNEL']

DESTINATION = "https://t.me/grzegorzistyping/"

client = TelegramClient('session_name', API_ID, API_HASH)
client.start()
client.parse_mode = "html"

# Paste min id here

# https://t.me/grzegorzkiselevwill/3597

messages = client.get_messages(CHANNEL, limit=9000, min_id=1910)
messages.reverse()

# f = open("messages.txt", "a")
# print(str(messages), "", "\n", file=f)
# f.close

album = []
def send_album(album):
    caption = None
    for message in album:
        if message.text != "":
            caption = message.text
            break
    
    try:
        client.send_message(DESTINATION, message=caption, file=album)
    except Exception as error:
        print(error)

l = 0
for r, message in enumerate(messages):

    time.sleep(1)

    if message.grouped_id == None:
        if len(album) > 0:
            send_album(album)
            album = []

        try:
            client.send_message(DESTINATION, message=message)
        except Exception as error:
            print(error)
        
        l = r
    else:
        if messages[l].grouped_id == None:
            l = r
        
        if messages[l].grouped_id != message.grouped_id:
            send_album(album)
            album = []
            l = r

        if messages[l].grouped_id == message.grouped_id:
            album.append(message)

        if r == len(messages) - 1:
            send_album(album)
