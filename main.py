import cv2
import numpy as np
import threading
import win32api
import win32con
import time
import pydirectinput
import keyboard

template_green_zone = cv2.imread('templates/GreenZone.png')
template_white_pillor = cv2.imread('templates/WhitePillor.png')
template_take_fish = cv2.imread('templates/TakeFish.png')
template_realease_fish = cv2.imread('templates/RealeasFish.png')
template_start_game = cv2.imread('templates/startGame.png')
template_take_realease = cv2.imread('templates/TakeOrRealease.png')
template_end_game = cv2.imread('templates/endGame.png')

def press_space():
    pydirectinput.press('space')

def hold_key(key):
    pydirectinput.keyDown(key.lower())

def release_key(key):
    pydirectinput.keyUp(key.lower())

def match_template(frame, template, threshold=0.8):
    result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    if max_val >= threshold:
        return max_loc
    return None

def match_template2(frame, template, threshold=0.05):
    result = cv2.matchTemplate(frame, template, cv2.TM_SQDIFF_NORMED)
    min_val, _, min_loc, _ = cv2.minMaxLoc(result)
    if min_val <= threshold:
        return min_loc
    return None

def is_near_or_inside(inner_pos, outer_pos, outer_size, tolerance=20):
    ix, iy = inner_pos
    ox, oy = outer_pos
    ow, oh = outer_size

    extended_left = ox - tolerance
    extended_right = ox + ow + tolerance
    extended_top = oy - tolerance
    extended_bottom = oy + oh + tolerance

    return extended_left <= ix <= extended_right and extended_top <= iy <= extended_bottom

def first_part_minigame(frame, green_zone_position, green_zone_size):
    h, w, _ = frame.shape
    roi_height = 120
    roi_width = int(w // 2.2)
    roi_x = (w - roi_width) // 2
    roi_y = h - roi_height

    roi = frame[roi_y:roi_y + 39, roi_x:roi_x + roi_width]

    # cv2.imshow('Debug ROI', roi)

    if green_zone_position is None:
        green_zone_position = match_template(roi, template_green_zone, threshold=0.75)

    if green_zone_position is not None:
        green_zone_position = (green_zone_position[0] - 10, green_zone_position[1])

    white_pillor_position = match_template(roi, template_white_pillor, threshold=0.7)

    if white_pillor_position and green_zone_position:
        if is_near_or_inside(white_pillor_position, green_zone_position, green_zone_size):
            print("Закидываем!")
            press_space()
            return True

        # debug_roi = roi.copy()
        # cv2.rectangle(debug_roi, green_zone_position,
        #               (green_zone_position[0] + green_zone_size[0],
        #                green_zone_position[1] + green_zone_size[1]),
        #               (0, 255, 0), 2)
        # cv2.rectangle(debug_roi, white_pillor_position,
        #               (white_pillor_position[0] + template_white_pillor.shape[1],
        #                white_pillor_position[1] + template_white_pillor.shape[0]),
        #               (255, 255, 255), 2)
        # cv2.imshow('Debug ROI', debug_roi)

    return False

def second_part_minigame(frame):
    h, w, _ = frame.shape
    roi_height = 100
    roi_width = int(w // 2.2) - 240
    roi_x = (w - roi_width) // 2 + 255
    roi_y = h - roi_height - 40

    roi = frame[roi_y:roi_y + 100, roi_x:roi_x + roi_width]
    # cv2.imshow('Debug StartGame', roi)

    start_game_position = match_template2(roi, template_start_game)
    if start_game_position:
        # debug_roi = roi.copy()
        # cv2.rectangle(debug_roi, start_game_position,
        #               (start_game_position[0] + start_game_position[0],
        #                start_game_position[1] + start_game_position[1]),
        #               (0, 255, 0), 2)
        #
        # cv2.imshow('Debug StartGame', debug_roi)
        press_space()
        return True
    return False

def third_part_minigame(frame):
    global prev_frame, holding_key

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    if prev_frame is not None:

        flow = cv2.calcOpticalFlowFarneback(prev_frame, gray, None,
                                            0.5, 3, 15, 3, 5, 1.2, 0)

        horizontal_flow = flow[..., 0]

        mean_flow = np.mean(horizontal_flow)

        if mean_flow > 0.7:
            if holding_key != 'D':
                release_key('A')
                hold_key('D')
                holding_key = 'D'
                print(f'зажимаем D')
        elif mean_flow < -0.7:
            if holding_key != 'A':
                release_key('D')
                hold_key('A')
                holding_key = 'A'
                print(f'зажимаем A')

    prev_frame = gray.copy()


def fourth_part_minigame(frame):
    h, w, _ = frame.shape

    roi_height = 120
    roi_width = int(w // 2.2) - 140
    roi_x = (w - roi_width) // 2
    roi_y = h - roi_height - 100

    search_roi_x = roi_x - 50
    search_roi_y = roi_y - 30
    search_roi_width = roi_width + 100
    search_roi_height = roi_height + 10

    search_roi_x = max(0, search_roi_x)
    search_roi_y = max(0, search_roi_y)
    search_roi_width = min(search_roi_width, w - search_roi_x)
    search_roi_height = min(search_roi_height, h - search_roi_y)

    search_roi = frame[search_roi_y:search_roi_y + search_roi_height,
                 search_roi_x:search_roi_x + search_roi_width]

    # cv2.imshow('Debug Finisher', search_roi)

    finisher_game_position = match_template2(search_roi, template_take_realease, threshold=0.2)
    if finisher_game_position:
        button_x = finisher_game_position[0] + template_take_realease.shape[1] // 2
        button_y = finisher_game_position[1] + template_take_realease.shape[0] // 2

        screen_x = search_roi_x + button_x
        screen_y = search_roi_y + button_y

        print(f"Обнаружена кнопка. Перемещаем мышь и кликаем")

        win32api.SetCursorPos((screen_x-30, screen_y+20))
        time.sleep(0.1)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.05)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        win32api.SetCursorPos((screen_x, screen_y-30))

        # debug_roi = search_roi.copy()
        # cv2.rectangle(debug_roi, finisher_game_position,
        #               (finisher_game_position[0] + template_take_realease.shape[1],
        #                finisher_game_position[1] + template_take_realease.shape[0]),
        #               (0, 255, 0), 2)
        # cv2.circle(debug_roi, (button_x, button_y), 5, (0, 0, 255), -1)
        # cv2.imshow('Debug Finisher', debug_roi)

        return True
    return False

def additional_end_minigame(frame):
    h, w, _ = frame.shape
    roi_height = 120
    roi_width = int(w // 2.2)
    roi_x = (w - roi_width) // 2
    roi_y = h - roi_height

    roi = frame[roi_y:roi_y + 39, roi_x:roi_x + roi_width]

    white_pillor_position = match_template(roi, template_white_pillor, threshold=0.9)
    if white_pillor_position:
        return True
    return False

def toggle_fishing():
    global fishing_active, answer, answer2,prev_frame,third_part_started,last_click_time,holding_key
    fishing_active = not fishing_active
    answer = False
    answer2 = False
    third_part_started = False
    prev_frame = None
    holding_key = None
    last_click_time = 0
    release_key('A')
    release_key('D')
    print("Авто-рыбалка ВКЛ 🟢" if fishing_active else "Авто-рыбалка ВЫКЛ 🔴")


cap = cv2.VideoCapture(4)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 800)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)

green_zone_position = None
green_zone_size = (55,9)
answer = False
prev_frame = None
holding_key = None
third_part_started = False
last_click_time = 0
fishing_active = False
end_game = False

keyboard.add_hotkey("F4", toggle_fishing)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_copy = frame.copy()

    if fishing_active:
        if third_part_started:
            third_part_minigame(frame)
            current_time = time.time()
            if current_time - last_click_time > 2.0:
                if fourth_part_minigame(frame_copy):
                    end_game = True
                elif additional_end_minigame(frame_copy):
                    end_game = True

                if end_game:
                    last_click_time = current_time
                    print('Рыбка поймана!')
                    answer = False
                    answer2 = False
                    end_game = False
                    third_part_started = False
                    release_key('A')
                    release_key('D')
                    holding_key = None
                    prev_frame = None
                    time.sleep(1)
        elif answer:
            answer2 = second_part_minigame(frame_copy)
            if answer2:
                third_part_started = True
        else:
            answer = first_part_minigame(frame_copy, green_zone_position, green_zone_size)

    #cv2.imshow('Fishing Mini-Game', frame_copy)
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()