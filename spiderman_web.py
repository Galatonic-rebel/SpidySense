import cv2
import mediapipe as mp
import time
import pygame


button_x = 20
button_y = 20
button_w = 200
button_h = 60
touch_start_time = None
web_sprite = cv2.imread("assets/web.png", cv2.IMREAD_UNCHANGED)



web_sprite = cv2.resize(
    web_sprite,
    (150, 100)
)

mega_web_sprite = cv2.resize(
    web_sprite,
    (350, 350)
)
def overlay_png(frame, png, x, y):

    h, w = png.shape[:2]

    if x < 0 or y < 0:
        return

    if x + w > frame.shape[1]:
        return

    if y + h > frame.shape[0]:
        return

    alpha = png[:, :, 3] / 255.0

    for c in range(3):

        frame[y:y+h, x:x+w, c] = (
            alpha * png[:, :, c]
            + (1 - alpha)
            * frame[y:y+h, x:x+w, c]
        )

pygame.mixer.init()

thwip_sound = pygame.mixer.Sound(
    "assets/thwip.mp3"
)


# MediaPipe setup
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

previous_tip_x = None
previous_tip_y = None

def finger_up(hand_landmarks, tip_id, pip_id):
    return hand_landmarks.landmark[tip_id].y < hand_landmarks.landmark[pip_id].y


previous_pose = False
webs = []
web_lines = []

attached_webs = []


last_shot_time = 0
SHOT_COOLDOWN = 0.5


cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()

    if not ret:
        break

    # Mirror effect
    frame = cv2.flip(frame, 1)

    # Convert BGR -> RGB
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Detect hands
    results = hands.process(rgb_frame)

    left_pose = False
    right_pose = False

    left_wrist_pos = None
    right_wrist_pos = None

    if results.multi_hand_landmarks and results.multi_handedness:

        h, w, _ = frame.shape

        for hand_landmarks, handedness in zip(
            results.multi_hand_landmarks,
            results.multi_handedness
        ):

            # Draw landmarks
            mp_draw.draw_landmarks(
                frame,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS
            )

            # Get fingertip position
            index_tip = hand_landmarks.landmark[8]

            tip_x = int(index_tip.x * w)
            tip_y = int(index_tip.y * h)

            inside_button = (
            button_x <= tip_x <= button_x + button_w
            and
            button_y <= tip_y <= button_y + button_h)
            
            if inside_button:
                attached_webs.clear()

            movement = 0

            if previous_tip_x is not None:
                movement = (
                    (tip_x - previous_tip_x) ** 2 +
                    (tip_y - previous_tip_y) ** 2
                ) ** 0.5

            previous_tip_x = tip_x
            previous_tip_y = tip_y

            

            # Hand label
            label = handedness.classification[0].label

            # Wrist position
            wrist = hand_landmarks.landmark[0]

            x = int(wrist.x * w)
            y = int(wrist.y * h)

            # Show Left/Right label
            cv2.putText(
                frame,
                label,
                (x, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 0, 0),
                2
            )

            # Finger states
            index_up = finger_up(hand_landmarks, 8, 6)
            middle_up = finger_up(hand_landmarks, 12, 10)
            ring_up = finger_up(hand_landmarks, 16, 14)
            pinky_up = finger_up(hand_landmarks, 20, 18)

            # Landmark 0 = wrist
            # Landmark 9 = center of palm

            wrist = hand_landmarks.landmark[0]
            middle_base = hand_landmarks.landmark[9]
            vertical_diff = middle_base.y - wrist.y

            

            
            cv2.putText(
                    frame,
                    f"Move: {movement:.1f}",
                    (50, 250),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 255),
                    2
                )
           

            # Spider-Man gesture
            spiderman_pose = (
                index_up and
                pinky_up and
                not middle_up and
                not ring_up 
            )

            if label == "Left":
                left_pose = spiderman_pose
                left_wrist_pos = (x, y)

            elif label == "Right":
                right_pose = spiderman_pose
                right_wrist_pos = (x, y)

            current_time = time.time()
            if (spiderman_pose and not previous_pose and 
            current_time - last_shot_time > SHOT_COOLDOWN and movement > 80):
                index_tip = hand_landmarks.landmark[8]
                wrist = hand_landmarks.landmark[0]

                tip_x = int(index_tip.x * w)
                tip_y = int(index_tip.y * h)

                wrist_x = int(wrist.x * w)
                wrist_y = int(wrist.y * h)

                dx = tip_x - wrist_x
                dy = tip_y - wrist_y

                length = (dx**2 + dy**2) ** 0.5

                if length != 0:
                    dx /= length
                    dy /= length

                webs.append([tip_x, tip_y, dx, dy, tip_x, tip_y])

                thwip_sound.stop()
                thwip_sound.play()
                last_shot_time = current_time
        
        previous_pose = spiderman_pose
    
    if (
        left_pose and
        right_pose and
        left_wrist_pos is not None and
        right_wrist_pos is not None
    ):
        mega_web_active = True
        print("MEGA WEB ACTIVATED")
       
    for web in webs:
        speed = 25
        web[0] += web[2] * speed
        web[1] += web[3] * speed

        x1, y1 = int(web[4]), int(web[5])
        x2, y2 = int(web[0]), int(web[1])

        MAIN_COLOR = (62, 53, 58)
        SIDE_COLOR = (80, 70, 75)

        dx = web[2]
        dy = web[3]

        perp_x = -dy
        perp_y = dx

        distance = ((x2 - x1)**2 + (y2 - y1)**2) ** 0.5
        spread = min(30, int(distance / 8))

        left_tip_x = int(x2 + perp_x * spread)
        left_tip_y = int(y2 + perp_y * spread)

        right_tip_x = int(x2 - perp_x * spread)
        right_tip_y = int(y2 - perp_y * spread)

        if distance > 100:
            attached_webs.append([x2, y2])
            web[0] = -9999
    

       

        cv2.line(
            frame,
            (x1, y1),
            (left_tip_x, left_tip_y),
            SIDE_COLOR,
            1
        )

        cv2.line(
            frame,
            (x1, y1),
            (x2, y2),
            MAIN_COLOR,
            1
        )

        cv2.line(
            frame,
            (x1, y1),
            (right_tip_x, right_tip_y),
            SIDE_COLOR,
            1
        )

    for attached in attached_webs:
        ax, ay = attached
        overlay_png(
                frame,
                web_sprite,
                ax - web_sprite.shape[1] // 2,
                ay - web_sprite.shape[0] // 2
            )

      
            

      
    
    webs = [web for web in webs
            if web[0] > 0 and web[0] < w
            and web[1] > 0 and web[1] < h]
  

    # Default button color
    button_color = (0, 0, 255)  # Red

    # Turn green if finger is hovering
    if 'inside_button' in locals() and inside_button:
        button_color = (0, 255, 0)

    # Button rectangle
    cv2.rectangle(
        frame,
        (button_x, button_y),
        (button_x + button_w, button_y + button_h),
        button_color,
        -1
    )

    # Black outline text
    cv2.putText(
        frame,
        "RESET CITY",
        (button_x + 10, button_y + 45),
        cv2.FONT_HERSHEY_TRIPLEX,
        0.9,
        (0, 0, 0),
        5
    )

    # Red/white foreground text
    cv2.putText(
        frame,
        "RESET CITY",
        (button_x + 10, button_y + 45),
        cv2.FONT_HERSHEY_TRIPLEX,
        0.9,
        (255, 255, 255),
        2
    )
    


    cv2.imshow("SpidySense", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

  


cap.release()
cv2.destroyAllWindows()