import json
import logging
import sys
import threading
import time
import cv2
import pygame
from djitellopy import Tello
import KeyPressModule as kp
import os
import datetime
from tkinter import simpledialog
import tkinter as tk
import socket

kp.init()

logs_folder = "logs"
if not os.path.exists(logs_folder):
    os.makedirs(logs_folder)
video_folder = "videos"
if not os.path.exists(video_folder):
    os.makedirs(video_folder)

# Проверка наличия папки с логами и создание, если она не существует
if not os.path.exists(logs_folder):
    os.makedirs(logs_folder)

# Создание имени файла лога на основе текущей даты и времени
log_file_name = f"keyboard_input_log_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"

# Создание пути к файлу лога
log_file_path = os.path.join(logs_folder, log_file_name)

# Инициализация логгера
logging.basicConfig(filename=log_file_path, level=logging.INFO, format='%(asctime)s - %(message)s')

def get_server_address():
    """
    Запрашивает у пользователя IP-адрес сервера и порт.

    Возвращает:
    - tuple, содержащий IP-адрес и порт.
    """
    root = tk.Tk()
    root.withdraw()
    create_config_if_not_exists()
    previous_ip, previous_port = load_config()
    initial_value = f"{previous_ip}:{previous_port}" if previous_ip and previous_port else ""
    input_str = simpledialog.askstring("Input", "Enter server IP address and port (IP:port):", initialvalue=initial_value)
    if input_str is not None:
        try:
            ip_address, port = input_str.split(':')
            save_config(ip_address, port)
            return ip_address, int(port)
        except ValueError:
            return get_server_address()  # Повторный запрос в случае неверного формата
    else:
        root.destroy()  # Закрываем окно
        sys.exit(0)  # Завершаем выполнение программы

def save_config(ip_address, port):
    """
    Сохраняет IP-адрес и порт в файле конфигурации.

    Параметры:
    - ip_address: str, IP-адрес сервера.
    - port: int, порт сервера.
    """
    with open(CONFIG_FILE, "w") as f:
        config = {"ip_address": ip_address, "port": port}
        json.dump(config, f)

def load_config():
    """
    Загружает IP-адрес и порт из файла конфигурации.

    Возвращает:
    - tuple, содержащий IP-адрес и порт сервера.
    """
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            ip_address = config.get("ip_address")
            port = config.get("port")
            if ip_address and port:
                return ip_address, int(port)
            else:
                return None, None
    except (FileNotFoundError, json.JSONDecodeError):
        return None, None

def create_config_if_not_exists():
    """
        Создает файл конфигурации, если он не существует.
        """
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump({}, f)

CONFIG_FILE = "config.json"
ip_address, port = get_server_address()
me = Tello(ip_address, port)
logging.info("Drone connected: %s" % me.connect())
frame_buffer = []

java_host = '192.168.1.102'
print(me.get_battery())
logging.info("Drone battery: %s" % me.get_battery())
me.streamon()

#Сокет для передачи команд управления с клавитауры на очки
java_host = '192.168.1.101'
java_port = 8080
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

#Сокет для принятия команд от EMG (TCP)
SERVER_IP = '127.0.0.1'
SERVER_PORT = 8999
server_socket_nm_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket_nm_client.bind((SERVER_IP, SERVER_PORT))
server_socket_nm_client.listen(1)
color_white = (255,255,255)
# Создание имени файла на основе текущей даты и времени
video_file_name = f"video_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.mp4"
video_file_path = os.path.join(video_folder, video_file_name)

# Инициализация объекта VideoWriter
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(video_file_path, fourcc, 60.0, (640, 480))

global img

#Метод для оперирование клавитатурой
def getKeyboardInput():
    """
   Функция отвечающая за получение команд от клавиатуры и обработку действий.

   Returns:
   - list: Список значений управления (left/right, forward/backward, up/down, yaw velocity).
   """
    lr, fb, ud, yv = 0, 0, 0, 0
    speed = 50

    try:
        if kp.getKey("LEFT"):
            lr = -speed
        elif kp.getKey("RIGHT"):
            lr = speed

        if kp.getKey("UP"):
            fb = speed
        elif kp.getKey("DOWN"):
            fb = -speed

        if kp.getKey("w"):
            ud = speed
        elif kp.getKey("s"):
            ud = -speed

        if kp.getKey("a"):
            yv = -speed
        elif kp.getKey("d"):
            yv = speed

        if kp.getKey("q"):
            me.land()
            logging.info("Drone landed")

        if kp.getKey("ESCAPE"):
            out.release()
            me.land()
            me.end()
            pygame.quit()
            logging.info("Drone disconnected and program exited")
            sys.exit(0)

        if kp.getKey("e"):
            me.takeoff()
            logging.info("Drone took off")

        if kp.getKey("z"):
            cv2.imwrite(f'Resources/Images/{time.time()}.jpg', img)
            logging.info("Image saved")
            time.sleep(0.3)

    except Exception as e:
        logging.error(f"Error in keyboard input: {e}")
        print(f"Error in keyboard input: {e}")

    return [lr, fb, ud, yv]


last_lr, last_fb, last_ud, last_yv = 0, 0, 0, 0



while True:
    try:
        vals = getKeyboardInput()
        me.send_rc_control(vals[0], vals[1], vals[2], vals[3])
        if (vals[0], vals[1], vals[2], vals[3]) != (last_lr, last_fb, last_ud, last_yv):
            logging.info("Speed now: %s" % [vals[0], vals[1], vals[2], vals[3]])
            last_lr, last_fb, last_ud, last_yv = vals[0], vals[1], vals[2], vals[3]

        img = me.get_frame_read().frame
        if img is not None:
            img = cv2.resize(img, (640, 480))
            frame_buffer.append(img)

        if len(frame_buffer) > 2:
            for frame in frame_buffer:
                out.write(frame)
                frame_buffer.clear()

        #cv2.putText(img, f"Baterry level: {me.get_battery()}", (10,30),cv2.FONT_HERSHEY_SIMPLEX, 1, color_white, 1)
        cv2.imshow("Image", img)
        cv2.waitKey(1)


    except Exception as e:
        logging.error(f"Error in main loop: {e}")
        print(f"Error in main loop: {e}")
