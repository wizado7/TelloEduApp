
import json
import logging
import sys
import threading
from queue import Queue
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
    if input_str is not None:  # Проверяем, что пользователь не нажал "Cancel" или закрыл диалог
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
print(me.get_battery())
me.streamon()


#Сокет для принятия команд от EMG (TCP)
SERVER_IP = '127.0.0.1'
SERVER_PORT = 8999
server_socket_nm_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket_nm_client.bind((SERVER_IP, SERVER_PORT))
server_socket_nm_client.listen(1)


# Создание имени файла на основе текущей даты и времени
video_file_name = f"video_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.mp4"
video_file_path = os.path.join(video_folder, video_file_name)

# Инициализация объекта VideoWriter
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(video_file_path, fourcc, 60.0, (640, 480))

global img

def input_key():
    if kp.getKey("e"):
        me.takeoff()
    elif kp.getKey("q"):
        me.land()
    elif kp.getKey("ESCAPE"):
        out.release()
        me.land()
        me.end()
        pygame.quit()
        sys.exit(0)
    else:
        pass


def receive_emg_commands():
    global data_client_command
    while True:
        client_socket_nm_client, client_address_nm_client = server_socket_nm_client.accept()
        data_client = client_socket_nm_client.recv(1024)
        a = []
        for i in range(int(len(data_client) / 4)):
            a.append(data_client[i * 4])

        data_client_command = a
        print(data_client_command)
        client_socket_nm_client.close()

def commandLisenterFromNM():
    """
    Функция отвечающая за обработку команд от дополнительных программ

    Returns:
    - list: Список значений управления (left/right, forward/backward, up/down, yaw velocity).
    """
    global data_client_command
    lr, fb, ud, yv = 0, 0, 0, 0
    speed = 50
    print(data_client_command)

    if data_client_command == [1, 0, 0, 0, 0, 0, 0, 0]:
        fb = speed
    elif data_client_command == [0, 1, 0, 0, 0, 0, 0, 0]:
        fb = -speed
    elif data_client_command == [0, 0, 0, 1, 0, 0, 0, 0]:
        lr = speed
    elif data_client_command == [0, 0, 1, 0, 0, 0, 0, 0]:
        lr = -speed
    elif data_client_command == [0, 0, 0, 0, 1, 0, 0, 0]:
        ud = speed
    elif data_client_command == [0, 0, 0, 0, 0, 1, 0, 0]:
        ud = -speed
    elif data_client_command == [0, 0, 0, 0, 0, 0, 1, 0]:
        yv = speed
    elif data_client_command == [0, 0, 0, 0, 0, 0, 0, 1]:
        yv = -speed

    return [lr, fb, ud, yv]

def start_emg_loop():
    last_lr, last_fb, last_ud, last_yv = 0, 0, 0, 0
    frame_buffer = []
    while True:
        try:
            input_key()
            vals = commandLisenterFromNM()
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

            cv2.imshow("Image", img)
            cv2.waitKey(1)

        except Exception as e:
            print(f"Error in EMG loop: {e}")


emg_thread = threading.Thread(target=receive_emg_commands)
emg_thread.daemon = True
emg_thread.start()

if __name__ == '__main__':
    start_emg_loop()