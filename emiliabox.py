#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from time import sleep
from time import time
import os
import RPi.GPIO as GPIO
import serial
from serial.tools import list_ports
import mpd
import signal
import sys
import random
# import pyaudio
import errno
import numpy
import math
import copy
import pickle
import subprocess
import logging
import argparse
from collections import deque
home_path = '/home/danst/'

class Display:
    port = '/dev/ttyUSB0'
    ser = None
    def __init__(self):
        """Initialisiere den seriellen Port und das Display"""
        try:    
            self.serial_port = serial.Serial(self.port, 19200, timeout=2)
        except:
            self.serial_port = None
        # Kurz warten, damit sich das Display initialisiert
        sleep(3)
        
    def write_int(self, ints):
        if self.serial_port != None:
            for i in ints:
#             self.serial_port.write(bytes(i, 'integer'))
                self.serial_port.write(bytes(chr(i), 'latin-1'))
    
    

    def clear_wb(self):
        # 72 08 00 00 cc rr gg bb    
        self.write_int([0x52, 0x08, 0x00, 0x00, 0x00])
    def swap_wb_display(self):
        #52 1F 00 00 00
        self.write_int([0x52, 0x1f, 0x00, 0x00, 0x00])
    def draw_letter_wb(self, letter, pos=(0x00, 0x00), rgb=(0xff, 0xff, 0xff)):
        # 72 06 xx yy ii rr gg bb
        self.write_int([0x72, 0x06, pos[0], pos[1], ord(letter), rgb[0], rgb[1], rgb[2]])
    def roll_wb(self, pixel=(1,0), rgb=(0x0, 0x0, 0x0)):
        # 72 23 xx yy 00 00 00 00
        self.write_int([0x72, 0x20, pixel[0], pixel[1], 0x00, 0x00, 0x00, 0x00])
    def off(self):
        self.write_int([0x52, 0x03, 0x00, 0x00, 0x00, 0x00])
        
    def exit(self):
        """Serielle Schnittstelle wieder freigeben"""
        self.off()
        if self.serial_port != None:
            self.serial_port.close()
        
    def test_animation(self):
        """Play a test animation"""
        self.show_picture('test')

    def show_picture(self, name):
        """Display a picture"""
        test_file = home_path + name +'.rbd'
        file = open(test_file, 'rb')
        commands = file.read()
        if self.serial_port != None:
            self.serial_port.write(commands)
        file.close()

    def print_text():
        """Print and scroll text"""
        pass
    
        
class Buttons:
    def __init__(self):
        self.up_pin = 8
        self.down_pin = 7
        self.select_pin = 25
        self.off_pin = 18
        self.channel_select_pin = 23
        GPIO.setup(self.up_pin, GPIO.IN)
        GPIO.setup(self.down_pin, GPIO.IN)
        GPIO.setup(self.select_pin, GPIO.IN)
        GPIO.setup(self.channel_select_pin, GPIO.IN)
        GPIO.setup(self.off_pin, GPIO.IN)
        self.key = ''
        self.button_last_pressed = {}
        self.key_threshold = 0.5
        self.key_pressed = {self.up_pin: 0, self.down_pin: 0, self.select_pin: 0, self.off_pin: 0, self.channel_select_pin: 0}
    
    def get_pin(self, pin_no, echt=False):
#         print(pin_no, echt)
        pressed = False
        if pin_no in self.button_last_pressed.keys():
            if (time() - self.button_last_pressed[pin_no] > self.key_threshold) or (echt == True):
#                 print('chekc')
                if GPIO.input(pin_no) == self.key_pressed[pin_no]:
                    
#                     print('Pin', pin_no, 'wurde gedrückt')
                    pressed = True
                    self.button_last_pressed[pin_no] = time()
        else:
            self.button_last_pressed[pin_no] = time()
        return pressed
    def get_select_button(self):
        return self.get_pin(self.select_pin)
#         return self.get_key('a')

    def get_up_button(self):
        #return GPIO.input(23)
        return self.get_pin(self.up_pin)
#         return self.get_key('h')
    
    def get_down_button(self):
        return self.get_pin(self.down_pin)
    
    def get_off_switch(self):
        return self.get_pin(self.off_pin, True)
    
    def get_channel_select_button(self):
        return self.get_pin(self.channel_select_pin)
        
    def exit(self):
        pass
        
class single_led:
    def __init__(self, pin):

        GPIO.setup(pin, GPIO.OUT)
        self.pin = pin
        self.status = False
        self.off()
    def on(self):
        GPIO.output(self.pin, GPIO.LOW)
        self.status = True
    def off(self):
        GPIO.output(self.pin, GPIO.HIGH)
        self.status = False
    def toggle(self):
        if self.status:
            self.off()
        else:
            self.on()
    
class LEDs:
    def __init__(self):
        self.red_pin = 27
        self.green_pin = 22
        self.yellow_pin = 17
        self.red = single_led(self.red_pin)
        self.yellow = single_led(self.yellow_pin)
        self.green = single_led(self.green_pin)
        
        
    def exit(self):
        pass

class Emilia_OS:
    """Do all the background stuff and launch applications"""
    def __init__(self, quiet):
        GPIO.setmode(GPIO.BCM)
        self.led = LEDs()
        self.button = Buttons()
        self.display = Display()
        self.app_icon = 'Haus'
        if not quiet:
            self.play_audio_file('res/MacStartUp.mp3', background=True)
        self.display.show_picture(self.app_icon)
        sleep(1)
        self.connect_mpd()
        command = ['/usr/bin/mpc', 'volume', '100']
        subprocess.call(command, stdout=open(os.devnull, 'w'))

        self.play_status_before_standby = ''
        self.pickle_file = home_path + 'pickle.pk'
        try:
            self.pick = open(self.pickle_file, 'rb')
            self.app_switch = pickle.load(self.pick)
            self.pick.close()
        except:
            self.app_switch = 0
        self.go_exit = False
        signal.signal(signal.SIGINT, self.signal_handler)

        self.apps = [Music_App(self), Visualizer_App(self), Tunnel(self) ] #Einschlafen_App(self), Wecker_App(self), White_Noise_App(self)]
        self.show_icon()
        

    def connect_mpd(self):
        self.mpdaemon = mpd.MPDClient()
        self.mpdaemon.timeout = 15
        self.mpdaemon.idletimeout = None
        self.mpdaemon.connect("localhost", 6600)

        
    def exit(self):
        self.led.exit()
        self.button.exit()
        self.display.exit()
        for i in range(1,len(self.apps)):
            self.apps[i].exit()
        GPIO.cleanup()

        
    def show_icon(self):
        """Zeige das entsprechende Bild der nächsten App an"""
        if self.apps[self.app_switch].app_icon != '':
            self.display.show_picture(self.apps[self.app_switch].app_icon)
        else:
            self.display.off()
    def event_select(self):
        """Function called as soon as red button is pressed"""
        pass
    def event_up(self):
        """Function called as soon as red button is pressed"""
        pass
    def event_down(self):
        """Function called as soon as red button is pressed"""
        pass
    def refresh_display(self):
        """Das Display neu bemalen, für den Fall, dass es Änderungen gab."""
        pass
    def event_switched_away(self):
        pass
    def event_switched(self):
        """Function is called as soon as one switches to the app"""
        pass   
    def signal_handler(self, signal, frame):
        logging.info('Das Emilia-Betriebssystem wird heruntergefahren')
        self.go_exit = True
    def every_ten(self):
        """Function called every x seconds"""
        pass
    def make_off(self):
        self.display.off()
        self.play_status_before_standby = self.apps[0].get_play_status()
        if self.play_status_before_standby == 'play':
            self.apps[0].pause_music()
    def make_on(self):
        self.show_icon()
        if self.play_status_before_standby == 'play':
            self.apps[0].play_music()
    def run(self):
        """Continously run and check for events"""
        pause = 0.01
        every_ten_init = 2/pause
        every_ten = every_ten_init
        off_pressed = False
        while not self.go_exit:
#             self.button.key = input('Welche Taste ([K]anal, [A]uswahl, [H]och, [R]unter, [B]eenden)? ').lower()
#             print(self.button.key)
            # if self.button.key == 'b':
#                 self.go_exit = True
            
            old_off = off_pressed
            if self.button.get_off_switch():
                if off_pressed == False:
                    self.make_off()
                    off_pressed = True
            else:
                off_pressed = False
                if old_off == True:
                    self.make_on()

            if not off_pressed:
                self.apps[self.app_switch].refresh_display()
                every_ten -= 1
                if every_ten == 0:
                    self.apps[self.app_switch].every_ten()
                    every_ten = every_ten_init
                #self.go_exit = True
                if self.button.get_channel_select_button():
                    self.apps[self.app_switch].event_switched_away()
                    self.app_switch += 1
                    if self.app_switch >= len(self.apps):
                        self.app_switch = 0
                    self.pick = open(self.pickle_file, 'wb')
                    pickle.dump(self.app_switch, self.pick)
                    self.pick.close()
                    self.show_icon()
                    self.apps[self.app_switch].event_switched()
                if self.button.get_select_button():
    #                 self.display.test_animation()
                    self.apps[self.app_switch].event_select()
                if self.button.get_up_button():
    #                 self.display.test_animation()
                    self.apps[self.app_switch].event_up()
                if self.button.get_down_button():
    #                 self.display.test_animation()
                    self.apps[self.app_switch].event_down()
            else:
                if self.button.get_select_button():
                    self.play_audio_file('res/beep.mp3')
                    sleep(4)
                    if self.button.get_select_button():
                        self.shutdown_raspberry_pi()
                self.led.red.toggle()
                sleep(2)
            sleep(pause)
    
    def make_abs_path(self, path):
        if not path.startswith('/'):
            # relativer Pfad
            path = home_path + path
        return path
    
    def play_audio_file(self, mp3, background=False):
        command = ['/usr/bin/mplayer', '-really-quiet', self.make_abs_path(mp3), '>/dev/null']
        if background:
            subprocess.Popen(command) 
        else:
            subprocess.call(command)

    def shutdown_raspberry_pi(self):
        self.play_audio_file('res/beep.mp3')
        subprocess.call(['/sbin/shutdown', 'now'])

class Tunnel:
    """Wecker application"""
    def __init__(self, eos):
        """Register for events with EOS, ..."""
        self.eos = eos
        self.app_icon = 'Tunnel'
        self.flugzeug_position = 3
        self.letzte_flugzeug_position = self.flugzeug_position
        self.old_top = 1
        self.old_bottom = 4
        self.speed_init = 30
        self.speed = self.speed_init
        self.top_limits = deque([1,1,2,2,2,2,1])
        self.bottom_limits = deque([3,3,3,2,3,3,4])
        self.restart_game()
    def restart_game(self):
        self.points = 0        
    def exit(self):
        pass
    def event_switched_away(self):
        pass
    def event_switched(self):
        """Function is called as soon as one switches to the app"""
        # clear display on start and swap with working buffer
        # clear screen
#         self.eos.display.write_int([0x52, 0x08, 0x00, 0x00, 0x00])
        # swap with WB
#         self.eos.display.write_int([0x52, 0x1F, 0x00, 0x00, 0x00])
        # clear screen
#         self.eos.display.write_int([0x52, 0x08, 0x00, 0x00, 0x00])

    def event_select(self):
        """Function called as soon as red button is pressed"""
        pass        
    def event_up(self):
        """Function called as soon as blue button is pressed"""
        self.flugzeug_position = max(0, self.flugzeug_position - 1)
    def event_down(self):
        """Function called as soon as red button is pressed"""
        self.flugzeug_position = min(7, self.flugzeug_position + 1)


    def calculate_new_column(self, old_top, old_bottom):
        old_lücke = 7 - old_top - old_bottom
        lücke = min(6, max(1, old_lücke + random.randint(-2, 2)))
        top = min(6, max(0, old_top + random.randint(-2, 2)))
        if lücke + top > 7:
            top = 7 - lücke
        bottom = 7 - top - lücke
        
        return top, bottom
    def every_ten(self):
        """Function called every x seconds"""
        pass
    def within_current_limits(self, pos):
        top = self.top_limits[0]
        bottom = self.bottom_limits[0]
        print(pos+1, top, 8- bottom)
        if pos+1 > top and pos < 8 - bottom:
            return True
        else:
            print('peng')
            return False
    def set_new_column(self, top, bottom):
        self.old_top, self.old_bottom = top, bottom
        self.top_limits.append(top)
        self.top_limits.popleft()
        self.bottom_limits.append(bottom)
        self.bottom_limits.popleft()
        self.points += 1
    def refresh_display(self):

        self.speed -= 1
        if self.speed != 0:
            sleep(0.01)
            # Kopiere den display Puffer in den Arbeitspuffer
            self.eos.display.write_int([0x52, 0x1E, 0x00, 0x00, 0x00])
            # Male die letzte Position des Raumschiffs schwarz
            self.eos.display.write_int([0x72, 0x0B, 1, self.letzte_flugzeug_position, 0x00, 0x00, 0x00, 0x00])
            # Male die neue Position des Raumschiffs
            self.eos.display.write_int([0x72, 0x0B, 1, self.flugzeug_position, 0x00, 0xff, 0x00, 0x00])
            self.letzte_flugzeug_position = self.flugzeug_position
            # Tausche den display Puffer mit dem Arbeitspuffer
            self.eos.display.write_int([0x52, 0x1F, 0x00, 0x00, 0x00])
        else:
            self.speed = self.speed_init
        
    #         Scroll Display by one
            # 72 23 xx yy 00 00 00 00
            # Kopiere den display Puffer in den Arbeitspuffer
            self.eos.display.write_int([0x52, 0x1E, 0x00, 0x00, 0x00])
            # Male die letzte Position des Raumschiffs schwarz
            self.eos.display.write_int([0x72, 0x0B, 1, self.letzte_flugzeug_position, 0x00, 0x00, 0x00, 0x00])
            # Scrolle um 6 in die falsche Richtung
            self.eos.display.write_int([0x72, 0x23, 0x07, 0x00, 0x00, 0x00, 0x00, 0x00])
            # Male die neue Position des Raumschiffs
            self.eos.display.write_int([0x72, 0x0B, 1, self.flugzeug_position, 0x00, 0xff, 0x00, 0x00])
            self.letzte_flugzeug_position = self.flugzeug_position
            top, bottom = self.calculate_new_column(self.old_top, self.old_bottom)
    #         print(top, bottom)
            self.set_new_column(top, bottom)
            # Male die letzte Spalte Schwarz
    #         72 0A xx 00 cc rr gg bb
            self.eos.display.write_int([0x72, 0x0A, 0x07, 0x00, 0x00, 0x00, 0x00, 0x00])
            # Male einen Pixel
            for i in range(top):
                self.eos.display.write_int([0x72, 0x0B, 7, i, 0x00, 0x99, 0x99, 0xcc])
            for i in range(bottom):
                self.eos.display.write_int([0x72, 0x0B, 7, 7-i, 0x00, 0x33, 0x99, 0x33])
            # Tausche den display Puffer mit dem Arbeitspuffer
            self.eos.display.write_int([0x52, 0x1F, 0x00, 0x00, 0x00])
        if not self.within_current_limits(self.flugzeug_position):
#             self.eos.play_audio_file('res/beep.mp3', background=True)
            sleep(5)
            self.speed = 1

class Wecker_App:
    """Wecker application"""
    def __init__(self, eos):
        """Register for events with EOS, ..."""
        self.eos = eos
        
        self.app_icon = 'Wecker'
        self.mpdaemon = mpd.MPDClient()
        self.mpdaemon.timeout = 10
        self.mpdaemon.idletimeout = None
        self.mpdaemon.connect("localhost", 6600)
        self.random = False
    def exit(self):
        self.mpdaemon.close()
        self.mpdaemon.disconnect() 
    def event_switched_away(self):
        pass

    def event_switched(self):
        """Function is called as soon as one switches to the app"""
        pass
    def event_select(self):
        """Function called as soon as red button is pressed"""
        pass        
    def event_up(self):
        """Function called as soon as blue button is pressed"""
        
        pass
    def event_down(self):
        """Function called as soon as red button is pressed"""
        pass        
    def refresh_display(self):
        """Das Display neu bemalen, für den Fall, dass es Änderungen gab."""
        pass
    def every_ten(self):
        """Function called every x seconds"""
        pass

class Einschlafen_App:
    """Wecker application"""
    def __init__(self, eos):
        """Register for events with EOS, ..."""
        self.eos = eos
        
        self.app_icon = 'Wecker'
        self.mpdaemon = mpd.MPDClient()
        self.mpdaemon.timeout = 10
        self.mpdaemon.idletimeout = None
        self.mpdaemon.connect("localhost", 6600)
        self.random = False
    def exit(self):
        self.mpdaemon.close()
        self.mpdaemon.disconnect() 
    def event_switched_away(self):
        pass

    def event_switched(self):
        """Function is called as soon as one switches to the app"""
        pass
    def event_select(self):
        """Function called as soon as red button is pressed"""
        pass        
    def event_up(self):
        """Function called as soon as blue button is pressed"""

        self.eos.display.clear_wb()
        self.eos.display.draw_letter_wb('1')
#         self.eos.display.scroll_wb(pixel=(2,0))
        self.eos.display.draw_letter_wb('0', pos=(4,0))    
        self.eos.display.swap_wb_display()

    def event_down(self):
        """Function called as soon as red button is pressed"""
        pass        
    def refresh_display(self):
        """Das Display neu bemalen, für den Fall, dass es Änderungen gab."""
        pass
    def every_ten(self):
        """Function called every x seconds"""
        pass

class White_Noise_App:
    def __init__(self, eos):
        """Register for events with EOS, ..."""
        self.eos = eos
        self.app_icon = 'Noise'
        self.mplayer = None
    def event_switched_away(self):
        pass
        
    def event_switched(self):
        """Function is called as soon as one switches to the app"""
        self.mplayer = subprocess.Popen(['/usr/bin/mplayer', '-loop 2', 'res/whitenoise.mp3'])

    def event_select(self):
        """Function called as soon as red button is pressed"""
        pass
    def event_up(self):
        """Function called as soon as blue button is pressed"""
        pass
    def event_down(self):
        """Function called as soon as red button is pressed"""
        pass
    def refresh_display(self):
        """Das Display neu bemalen, für den Fall, dass es Änderungen gab."""
        pass
    def exit(self):
        pass
    def every_ten(self):
        """Function called every x seconds"""
        pass

class Visualizer_App:
    """Visualizer application"""

    def __init__(self, eos):
        """Register for events with EOS, ..."""
        self.eos = eos
        self.app_icon = ''
        subprocess.call(['/usr/bin/touch', '/tmp/mpd.fifo'])
        try:
            self.pcm = os.open('/tmp/mpd.fifo', os.O_RDONLY | os.O_NONBLOCK)
        except FileNotFoundError:
            logging.error('Konnte mich nicht mit MPD fifo verbinden.')
            self.pcm = None
           
        self.screen_buffer = [['' for i in range(8)] for j in range(8)]
        self.old_screen = [['other' for i in range(8)] for j in range(8)]
        self.current_song = self.get_current_song()
        self.maximum = 0
        self.minimum = 0

    def get_current_song(self):
        try:
            self.eos.mpdaemon.status()
        except mpd.ConnectionError as e:
            self.eos.connect_mpd()
        except IOError as e:
            print(e, 'Error occured and caught')
            self.eos.connect_mpd()
        if 'song' in self.eos.mpdaemon.status():
            return self.eos.mpdaemon.status()['song']
        else:
            return None

    def exit(self):
        os.close(self.pcm)
        self.eos.mpdaemon.close()
        self.eos.mpdaemon.disconnect()
        
    def load_playlist(self, list):
#         self.stop_music()
        self.eos.mpdaemon.load(list)
#         self.mpdaemon.play()

    def event_switched_away(self):
        pass
#         mpc disable output 2
#         self.eos.mpdaemon.disable('2')
        
    def event_switched(self):
        """Function is called as soon as one switches to the app"""
#         mpc enable output 2
#         self.eos.mpdaemon.enable('2')
        # clear display on start and swap with working buffer
        # clear screen
        self.eos.display.write_int([0x52, 0x08, 0x00, 0x00, 0x00])
        # swap with WB
        self.eos.display.write_int([0x52, 0x1F, 0x00, 0x00, 0x00])
        # clear screen
        self.eos.display.write_int([0x52, 0x08, 0x00, 0x00, 0x00])
        self.screen_buffer = [['' for i in range(8)] for j in range(8)]
        self.old_screen = [['other' for i in range(8)] for j in range(8)]
    def event_select(self):
        """Function called as soon as red button is pressed"""
        pass
    def event_up(self):
        """Function called as soon as blue button is pressed"""
        pass        
    def event_down(self):
        """Function called as soon as red button is pressed"""
        pass

    def safe_read(self, fd, size=1024):
        """reads data from a pipe and returns `None` on EAGAIN"""
        try:
            return os.read(fd, size)
        except BlockingIOError:
            return None
        except:
            raise
    def every_ten(self):
        """Function called every x seconds"""
        song = self.get_current_song()
        if self.current_song != song:
            logging.debug('Song change')
            self.current_song = song
 
    def show_visual_col(self, col, value):
        # 72 0B xx yy cc rr gg bb Value of a single pixel
        for i in range(value):
            if i < 4:
                self.write_int([0x72, 0x0B, col, 7-i, 0x00, 0x00, 0xff, 0x00])
            elif i < 7:
                self.write_int([0x72, 0x0B, col, 7-i, 0x00, 0x00, 0xff, 0xff])
            else:
                self.write_int([0x72, 0x0B, col, 7-i, 0x00, 0xff, 0x00, 0x00])

    def show_visual_old(self, values):
        # 52 08 0r gb 00 Sets the pixel values of all pixels.
        self.write_int([0x52, 0x08, 0x00, 0x00, 0x00])
        for i, val in enumerate(values):
            self.show_visual_col(i, val)
        self.old_values = values
        # Swap Working and Display Buffer 52 1F 00 00 00
        self.write_int([0x52, 0x1F, 0x00, 0x00, 0x00])

    def difference_to_screen(self):
        # Kopiere den display Puffer in den Arbeitspuffer
        self.eos.display.write_int([0x52, 0x1E, 0x00, 0x00, 0x00])
        for col, col_val in enumerate(self.screen_buffer):
            for row, val in enumerate(col_val):
#                 print(val, self.old_screen[col][row])
                if val != self.old_screen[col][row]:
                    if val == 'grün':
                        self.eos.display.write_int([0x72, 0x0B, col, 7-row, 0x00, 0x00, 0xff, 0x00])
                    elif val == 'gelb':
                        self.eos.display.write_int([0x72, 0x0B, col, 7-row, 0x00, 0xff, 0xff, 0x00])
                    elif val == 'rot':
                        self.eos.display.write_int([0x72, 0x0B, col, 7-row, 0x00, 0xff, 0x00, 0x00])
                    else:
                        self.eos.display.write_int([0x72, 0x0B, col, 7-row, 0x00, 0x00, 0x00, 0x00])
#         input()
        self.old_screen = copy.deepcopy(self.screen_buffer)
        # Tausche den display Puffer mit dem Arbeitspuffer
        self.eos.display.write_int([0x52, 0x1F, 0x00, 0x00, 0x00])
    def show_visual(self, values):
        for col, val in enumerate(values):
            for row in range(val):
                if row < 4: 
                    color = 'grün'
                elif row < 6:
                    color = 'gelb'
                else:
                    color = 'rot'
                self.screen_buffer[col][row] = color
            # Obere Zeilen löschen
            for row in range(val, 8):
#                 print(col, row)
                self.screen_buffer[col][row] = ''
        self.difference_to_screen()
    
    def refresh_display(self):
        """Das Display neu bemalen, für den Fall, dass es Änderungen gab."""
        data = self.safe_read(self.pcm)
        if data != None and len(data) > 0:
            n = len(data)
            indata = numpy.fromstring(data, dtype=numpy.int16)
            spectrum = abs(numpy.fft.fft(indata/n))**2
            values = []
            pixels = 8
            start = 0
            end = 0
            geo_factor = 0.05
            for i in range(pixels):
                # nur die erste Hälfte des Spektrums verwenden
                end = start + (len(spectrum)/2) / pixels
                current = numpy.median(spectrum[start:end])
                try:
                    values.append(math.log(current))
                except:
                    values.append(0)
                start = end
            self.maximum = geo_factor * max(values) + (1-geo_factor) * self.maximum #max(max(values), self.maximum) # 
            self.minimum = geo_factor * min(values) + (1-geo_factor) * self.minimum # min(min(values), self.minimum)
            for i, val in enumerate(values):
                try:
                    values[i] = min(max(round(((val - self.minimum) / (self.maximum - self.minimum) ) * pixels), 0), 8)
                except:
                    values[i] = 0
            self.show_visual(values)           

class Music_App:
    """Music application"""    
    
    def __init__(self, eos):
        """Register for events with EOS, ..."""
        self.eos = eos
        self.app_icon = 'Musik'
        self.playlists = ['Kinder vom Kleistpark', 'Kinder vom Kleistpark 2', 'Kinder', 'Spaß', 'Ruhig', 'Emilia', 'Klassik', 'Beethoven Symphonien']
        try:
            self.eos.mpdaemon.update()
        except:
            pass
        self.pickle_file = home_path + 'pickle_pl.pk'
        try:
            self.pick = open(self.pickle_file, 'rb')
            self.playlist_counter = pickle.load(self.pick)
            self.pick.close()
        except:
            self.playlist_counter = 0
        # Sicherstellen, dass der Spiellistenzähler zwischen 0 und der Zahl der Playlisten liegt
        self.playlist_counter = min(max(0, self.playlist_counter), len(self.playlists)-1)
        self.random = False
        self.load_playlist(self.playlists[self.playlist_counter])
        self.maximum = 0
        self.minimum = 9999999
    def every_ten(self):
        """Function called every x seconds"""
        pass
    
    def get_play_status(self):
        try:
            self.eos.mpdaemon.status()
        except mpd.ConnectionError as e:
            self.eos.connect_mpd()
        except IOError as e:
            print(e, 'Error occured and caught')
            self.eos.connect_mpd()
#         print(self.eos.mpdaemon.status())
        return self.eos.mpdaemon.status()['state']

    def get_random_status(self):
        try:
            self.eos.mpdaemon.status()
        except mpd.ConnectionError as e:
            self.eos.connect_mpd()
        except IOError as e:
            print(e, 'Error occured and caught')    
            self.eos.connect_mpd()
        return self.eos.mpdaemon.status()['random']

    def exit(self):
        self.eos.mpdaemon.close()
        self.eos.mpdaemon.disconnect()
    def load_playlist(self, list, repeat=False):
        try:
            self.eos.mpdaemon.load(list)
        except mpd.ConnectionError as e:
            self.eos.connect_mpd()
            if not repeat:
                self.load_playlist(list, repeat=True)

    def play_music(self, repeat=False):
        try:
            self.eos.mpdaemon.play()
        except mpd.ConnectionError as e:
            self.eos.connect_mpd()
            if not repeat:
                self.play_music(repeat=True)
        except Exception as e:
            print("Unexpected error:", e)
            
    def pause_music(self, repeat=False):
        try:
            self.eos.mpdaemon.pause()
        except mpd.ConnectionError as e:
            self.eos.connect_mpd()
            if not repeat:
                self.pause_music(repeat=True)
        except Exception as e:
            print("Unexpected error:", e)
    
    def stop_music(self, repeat=False):
        try:
            self.eos.mpdaemon.clear()
        except:
            self.eos.connect_mpd()
            if not repeat:
                self.stop_music(repeat=True)
    
    def event_switched_away(self):
        """Function is called as soon as one switches to the app"""
        pass
    
    def event_switched(self):
        """Function is called as soon as one switches to the app"""
        pass
        
    def event_select(self):
        """Function called as soon as red button is pressed"""
#         print(self.get_play_status())
        if self.get_play_status() == 'pause': 
            self.play_music()
        else: 
            self.pause_music()
        
    def event_up(self):
        """Function called as soon as blue button is pressed"""
        if self.get_play_status() == 'pause':
            if self.get_random_status() == '0':
                self.eos.mpdaemon.random(1)
                self.eos.display.show_picture('Zufall_ein')
                sleep(2)
                self.eos.display.show_picture(self.app_icon)
            else:
                self.eos.mpdaemon.random(0)
                self.eos.display.show_picture('Zufall_aus')
                sleep(2)
                self.eos.display.show_picture(self.app_icon)
        else: # Playing
            self.eos.mpdaemon.next()
        
    def event_down(self):
        """Function called as soon as red button is pressed"""
        if self.get_play_status == 'pause':
            pass
        else: # Playing
            self.playlist_counter += 1
            if self.playlist_counter == len(self.playlists):
                self.playlist_counter = 0
            self.pick = open(self.pickle_file, 'wb')
            pickle.dump(self.playlist_counter, self.pick)
            self.pick.close()
            logging.info('lade liste ' + self.playlists[self.playlist_counter])
            self.stop_music()
            self.load_playlist(self.playlists[self.playlist_counter])
            self.play_music()
        
    def refresh_display(self):
        """Das Display neu bemalen, für den Fall, dass es Änderungen gab."""


if __name__ == '__main__':
    random.seed()
    logging.basicConfig(filename=home_path + 'emiliabox.log',level=logging.DEBUG)
    logging.basicConfig(format='%(asctime)s %(message)s')
    logging.info('Starte das Emilia-Betriebssystem')
    parser = argparse.ArgumentParser(description='Emilia-Musikbox Steuerungsprogramm', prog='Emilia OS')
    parser.add_argument('--leise', action="store_true", default=False, dest='leise', help='Keine lauten Töne')
    args = parser.parse_args()
#     print(args)
    eos = Emilia_OS(quiet=args.leise)
    eos.run()
    eos.exit()