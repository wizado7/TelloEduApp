"""
Данный скрипт написан как пример заранее подгтовленного маршрута для дрона.
Список всех команд в инструкции.
"""



from djitellopy import tello

from time import sleep

me = tello.Tello('192.168.10.1', 8889)

me.connect()

print(me.get_battery())

me.takeoff()

me.send_rc_control(0, 50, 0, 0)

sleep(2)

me.send_rc_control(0, 0, 0, 30)

sleep(2)

me.send_rc_control(0, 0, 0, 0)

me.land()