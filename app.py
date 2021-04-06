import sys
import os
import re
import pyocr
import pyocr.builders
import pyautogui
import cv2
import logging

from PIL import Image
from time import sleep

log_level = os.environ.get('log_level')
formatter = '='*50 + '\n[%(levelname)s] %(message)s'
if log_level == 'debug':
    logging.basicConfig(level=logging.DEBUG, format=formatter)
else:
    logging.basicConfig(level=logging.INFO, format=formatter)
logger = logging.getLogger(__name__)

# Setting of PyOCR
TESSERACT_PATH = 'C:\Program Files\Tesseract-OCR'
TESSDATA_PATH = 'C:\Program Files\Tesseract-OCR\\tessdata'

os.environ["PATH"] = os.pathsep + TESSERACT_PATH
os.environ["TESSDATA_PREFIX"] = TESSDATA_PATH

tools = pyocr.get_available_tools()
assert len(tools) > 0, 'OCR tool not found!!'
tool = tools[0]

logger.info(f'Will use tool {tool.get_name()}')

langs = tool.get_available_languages()
logger.info(f'Available languages: {",".join(langs)}')
lang = langs[0]
logger.info(f'Will use lang {lang}')

def pos_get(wait=3):
    '''
    範囲指定のためのマウスカーソルの座標を取得する
    メッセージボックスの左上と右下の端点で囲前れた範囲のスクリーンショットを撮る
    '''
    logger.info('Get position of left top in 3 sec.')
    sleep(wait)
    x1, y1 = pyautogui.position()
    logger.info(f'Position: x1:{x1}, y1:{y1}')

    logger.info('Get position of right bottom in 3 sec.')
    sleep(wait)
    x2, y2 = pyautogui.position()
    logger.info(f'Position: x2:{x2}, y2:{y2}')

    # PyAUtoGUIのregionの仕様に従って、相対座標を求める
    x2 -= x1
    y2 -= y1

    return (x1, y1, x2, y2)

def get_screen_shot(x1, y1, x2, y2, filepath):
    '''
    スクリーンショットを撮る
    グレースケール化してリサイズする
    '''
    sc = pyautogui.screenshot(region=(x1, y1, x2, y2)) # スクリーンショットを撮る
    sc.save(filepath)
    # 画像を拡大する
    img = cv2.imread(filepath)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    tmp = cv2.resize(gray, (gray.shape[1]*2, gray.shape[0]*2), interpolation=cv2.INTER_LINEAR)
    cv2.imwrite(filepath, tmp)

def recognize_character(filepath, lang='jpn'):
    '''
    画像を展開して文字認識する
    '''
    txt = tool.image_to_string(
        Image.open(filepath),
        lang=lang,
        builder=pyocr.builders.TextBuilder(tesseract_layout=6)
    ).replace('|', '').replace(' ', '').rstrip()
    logger.debug(f'''Recognized Text:
    {txt}''')
    return txt.split('\n')

def extract_damage(texts):
    for text in texts:
        m = re.match(
            r'([ァ-ン].+)に([0-9]+).*ダメージ.*',
            text
        )
        if m is not None:
            break

    if m is None:
        logger.debug('Recognition failed!')
        return

    name = m.groups()[0]
    damage = int(m.groups()[1])
    return {'name': name, 'damage': damage}

def calc_hp(current_hp, damage):
    left_hp = current_hp - damage.get('damage')
    logger.info(f'{damage.get("name")}に{damage.get("damage")}のダメージ')
    logger.info(f'{damage.get("name")}の残りHPは{left_hp}です')
    return left_hp

if __name__ == '__main__':
    wait = 0.0
    output_dir = 'output'
    fname = 'screenshot.png'
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, fname)
    # Define position
    x1, y1, x2, y2 = pos_get()

    current_hp = 9000
    prev_text = ''
    while True:
        get_screen_shot(x1, y1, x2, y2, filepath)
        text = recognize_character(filepath)
        if prev_text == text:
            logger.debug(f'The message is completely the same.\n'\
            f'I will retry in {wait} seconds.')
            sleep(wait)
            continue
        damage = extract_damage(text)
        if damage:
            current_hp = calc_hp(current_hp, damage)
        prev_text = text
        sleep(wait)
    
    logger.info('Program is over.')

