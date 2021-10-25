import re
import os

from flask import Flask, request, make_response

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.signature import SignatureVerifier
from slack_sdk.webhook import WebhookClient

from slack_bolt import App, Say
from slack_bolt.adapter.flask import SlackRequestHandler

# from utils import init_db, read_db, write_db, email_db, setup_db, insert_db

from utils import setup_db, insert_db
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# init_db()
# caught, score, spot, images = read_db()

db_caught, db_spot, db_images = setup_db()

caught, spot, images = {item['_id']: item['data'] for item in db_caught.find({})}, {item['_id']: item['data'] for item in db_spot.find({})}, {item['_id']: item['data'] for item in db_images.find({})}

# print(caught, spot, images)

token = os.environ.get("CLIENT_TOKEN")
client = WebClient(token=token)
SPOT_WORDS = ["spot", "spotted", "codespot", "codespotted"]
USER_PATTERN = r"<@[a-zA-Z0-9]{11}>"

prev = [None, None]
bolt_app = App(token=token, signing_secret=os.environ.get("SIGNING_SECRET"))

handler = SlackRequestHandler(bolt_app)

@app.route("/slack/events", methods=["POST"])
def handle_events():
    return handler.handle(request)

@bolt_app.event({
    "type": "message",
    "subtype": "file_share"
})
def log_spot(event, say):
    if any([w in event.get('text', '').lower() for w in SPOT_WORDS]):
        spotter = event['user']
        found_spotted = re.search(USER_PATTERN, event['text'])
        if not found_spotted:
            return
        spotted = found_spotted[0]
        spot[spotter] = spot.get(spotter, 0) + 1
        caught[spotted] = caught.get(spotted, 0) + 1
        for image in event['files']:
            images[spotted] = images.get(spotted, []) + [image['url_private']]
        global prev
        if spotter == prev[0]:
            prev[1] += 1
            if prev[1] >= 3:
                say(f"<@{spotter}> is on fire 🥵")
        else:
            prev[0] = spotter
            prev[1] = 1
        # write_db(caught, score, spot, images)
        # print(caught, spot, images)
        insert_db((db_caught, caught), (db_spot, spot), (db_images, images))
        response = client.reactions_add(channel=event['channel'], name="white_check_mark", timestamp=event['ts'])

@bolt_app.message("scoreboard")
@bolt_app.message("spotboard")
def scoreboard(event, say):
    scoreboard = sorted(spot.items(), key=lambda p: p[1], reverse=True)[:5]
    message = "Spotboard:\n" 
    for i in range(len(scoreboard)):
        curr = scoreboard[i]
        message += f"{i + 1}. <@{curr[0]}> - {curr[1]}\n" 
    say(message)

@bolt_app.message("caughtboard")
def caughtboard(event, say):
    caughtboard = sorted(caught.items(), key=lambda p: p[1], reverse=True)[:5]
    message = "Caughtboard:\n" 
    for i in range(len(caughtboard)):
        curr = caughtboard[i]
        message += f"{i + 1}. {curr[0]} - {curr[1]}\n" 
    say(message)

# TODO
@bolt_app.message("pics")
def pics(event, say):
    found_spotted = re.search(USER_PATTERN, event['text'])
    if not found_spotted:
        return
    spotted = found_spotted[0]
    message = f"Spots of {spotted}:\n"
    for link in images[spotted]:
        message += f"{link}\n"
    print(message)

@bolt_app.event("file_shared")
@bolt_app.event("message")
def ignore():
    pass

# https://stackoverflow.com/questions/21214270/how-to-schedule-a-function-to-run-every-hour-on-flask

# import time
# import atexit
# from apscheduler.schedulers.background import BackgroundScheduler

# scheduler = BackgroundScheduler()
# scheduler.add_job(func=email_db, trigger="interval", seconds=30)

# from flask_apscheduler import APScheduler

# scheduler = APScheduler()
# scheduler.init_app(app)
# scheduler.start()
# scheduler.add_job(func=email_db, trigger="interval", minutes=30, id='0')


if __name__ == '__main__':
    # scheduler.start()
    # atexit.register(lambda: scheduler.shutdown())
    app.run(threaded=True, port=5000)
    # bolt_app.start(5000)
