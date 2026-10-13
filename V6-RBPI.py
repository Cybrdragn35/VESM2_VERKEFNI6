
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from picamera2 import Picamera2
import asyncio
from aiomqtt import Client
from nicegui import ui, app

MQTT_BROKER = "10.201.48.166"
TOPIC = "0311kynning"
TOPIC_2 = "2007kynning"
TOPIC_3 = "1234kynning"
TOPIC_4 = "5678kynning"

counter = 0
eyesClosed = False
gognin = None
startBlink = False

curPlayer = ""

def uppfaera_gogn():
    pl1 = app.storage.general.get("pl1_score", 0)
    pl2 = app.storage.general.get("pl2_score", 0)

    if pl1 > pl2:
        gagna_label1.set_text(f"1st Place: PLAYER 1: {pl1} blinks")
        gagna_label2.set_text(f"2nd Place: PLAYER 2: {pl2} blinks")
    elif pl2 > pl1:
        gagna_label1.set_text(f"1st Place: PLAYER 2: {pl2} blinks")
        gagna_label2.set_text(f"2nd Place: PLAYER 1: {pl1} blinks")
    else:
        gagna_label1.set_text(f"TIE: PLAYER 1: {pl1} blinks")
        gagna_label2.set_text(f"TIE: PLAYER 2: {pl2} blinks")

async def mottaka(client):
    global startBlink
    global curPlayer

    await client.subscribe(TOPIC_2)
    await client.subscribe(TOPIC_3)
    await client.subscribe(TOPIC_4)

    async for message in client.messages:
        topic = str(message.topic)

        if topic == TOPIC_2:
            startBlink = message.payload.decode() == "True"

        elif topic == TOPIC_3:
            curPlayer = message.payload.decode()
            
        elif topic == TOPIC_4:
            pl1, pl2 = map(
                int,
                message.payload.decode().split()
            )

            app.storage.general["pl1_score"] = pl1
            app.storage.general["pl2_score"] = pl2

async def sendir(client):
    global counter

    while True:
        skilabod = str(counter).encode()
        await client.publish(TOPIC, skilabod)
        await asyncio.sleep(0.5)

async def main():
    async with Client(MQTT_BROKER) as client:
        await asyncio.gather(
            camera(),
            sendir(client),
            mottaka(client)
        )


def draw_landmarks_on_image(rgb_image, detection_result):
    annotated_image = rgb_image.copy()

    for face_landmarks in detection_result.face_landmarks:
        for connection in vision.FaceLandmarksConnections.FACE_LANDMARKS_TESSELATION:
            start = connection.start
            end = connection.end

            x1 = int(face_landmarks[start].x * annotated_image.shape[1])
            y1 = int(face_landmarks[start].y * annotated_image.shape[0])

            x2 = int(face_landmarks[end].x * annotated_image.shape[1])
            y2 = int(face_landmarks[end].y * annotated_image.shape[0])

            cv2.line(
                annotated_image,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                1
            )

        for connection in vision.FaceLandmarksConnections.FACE_LANDMARKS_CONTOURS:
            start = connection.start
            end = connection.end

            x1 = int(face_landmarks[start].x * annotated_image.shape[1])
            y1 = int(face_landmarks[start].y * annotated_image.shape[0])

            x2 = int(face_landmarks[end].x * annotated_image.shape[1])
            y2 = int(face_landmarks[end].y * annotated_image.shape[0])

            cv2.line(
                annotated_image,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
            )

    return annotated_image


base_options = python.BaseOptions(
    model_asset_path="face_landmarker.task"
)

options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    output_face_blendshapes=True,
    output_facial_transformation_matrixes=True,
    num_faces=1
)

detector = vision.FaceLandmarker.create_from_options(options)


async def camera():
    global counter
    global eyesClosed
    global startBlink
    global curPlayer3

    while True:
        while not startBlink:
            await asyncio.sleep(0.1)

        counter = 0
        eyesClosed = False

        print("CAMERA STARTING")

        picam2 = Picamera2()

        picam2.configure(
            picam2.create_preview_configuration(
                main={
                    "format": "RGB888",
                    "size": (120, 140)
                }
            )
        )

        picam2.start()
        while startBlink:

            frame = picam2.capture_array()

            image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=frame
            )

            detection_result = detector.detect(image)

            if detection_result.face_blendshapes:
                blendshapes = detection_result.face_blendshapes[0]

                left_eye = 0
                right_eye = 0

                for blendshape in blendshapes:
                    if blendshape.category_name == "eyeBlinkLeft":
                        left_eye = blendshape.score

                    if blendshape.category_name == "eyeBlinkRight":
                        right_eye = blendshape.score

                if left_eye > 0.5 and right_eye > 0.5:
                    if not eyesClosed:
                        eyesClosed = True

                else:
                    if eyesClosed:
                        eyesClosed = False
                        counter += 1
                        print(f"BLINKS: {counter}")

            annotated_image = draw_landmarks_on_image(
                image.numpy_view(),
                detection_result
            )

            cv2.imshow(
                "Face Landmarks",
                cv2.cvtColor(
                    annotated_image,
                    cv2.COLOR_RGB2BGR
                )
            )

            if cv2.waitKey(1) & 0xFF == ord("q"):
                return

            await asyncio.sleep(0.01)

        print(f"Round ended. Player: {curPlayer}")
        print(f"Total blinks: {counter}")

        picam2.stop()
        picam2.close()
        cv2.destroyAllWindows()

ui.label('leaderboard').classes('text-h2')
with ui.column():
    gagna_label1 = ui.label("1st - Engin gögn móttekin enn")
    gagna_label2 = ui.label("2nd - Engin gögn móttekin enn")

ui.timer(1.0, uppfaera_gogn)


app.on_startup(main)
ui.run(port=5000)