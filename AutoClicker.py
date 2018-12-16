from PIL import ImageGrab, ImageOps
import pyautogui
import time
from numpy import *
class Coordinates():
#Coordinates can be changed to wherever you want to AutoClick
    replayBtn = (100,350)

def restartGame():
    pyautogui.click(Coordinates.replayBtn)

while True:
    restartGame()
    time.sleep(0)
# warning there is no current way to stop the script once you run apart from shutting down your pc
