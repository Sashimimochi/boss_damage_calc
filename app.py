import sys
import os
import re
import pyocr
import pyocr.builders
import pyautogui
import cv2
import logging
import tkinter
import time
import pyautogui

from PIL import Image, ImageTk
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


RESIZE_RETIO = 2 # 縮小倍率の規定

# ドラッグ開始した時のイベント - - - - - - - - - - - - - - - - - - - - - - - - - - 
def start_point_get(event):
    global start_x, start_y # グローバル変数に書き込みを行なうため宣言

    canvas1.delete("rect1")  # すでに"rect1"タグの図形があれば削除

    # canvas1上に四角形を描画（rectangleは矩形の意味）
    canvas1.create_rectangle(event.x,
                             event.y,
                             event.x + 1,
                             event.y + 1,
                             outline="red",
                             tag="rect1")
    # グローバル変数に座標を格納
    start_x, start_y = event.x, event.y

# ドラッグ中のイベント - - - - - - - - - - - - - - - - - - - - - - - - - - 
def rect_drawing(event):

    # ドラッグ中のマウスポインタが領域外に出た時の処理
    if event.x < 0:
        end_x = 0
    else:
        end_x = min(img_resized.width, event.x)
    if event.y < 0:
        end_y = 0
    else:
        end_y = min(img_resized.height, event.y)

    # "rect1"タグの画像を再描画
    canvas1.coords("rect1", start_x, start_y, end_x, end_y)

# ドラッグを離したときのイベント - - - - - - - - - - - - - - - - - - - - - - - - - - 
def release_action(event):

    # "rect1"タグの画像の座標を元の縮尺に戻して取得
    start_x, start_y, end_x, end_y = [
        round(n * RESIZE_RETIO) for n in canvas1.coords("rect1")
    ]

    # 取得した座標を表示
    #pyautogui.alert("start_x : " + str(start_x) + "\n" + "start_y : " +
    #                str(start_y) + "\n" + "end_x : " + str(end_x) + "\n" +
    #                "end_y : " + str(end_y))
    
    global START_X
    global START_Y
    global END_X
    global END_Y
    START_X = start_x
    START_Y = start_y
    END_X = end_x - START_X
    END_Y = end_y - START_Y

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

def calc_hp(damage, filepath):
    current_hp = load_hp(filepath)
    left_hp = current_hp - damage.get('damage')
    logger.info(f'{damage.get("name")}に{damage.get("damage")}のダメージ')
    logger.info(f'{damage.get("name")}の残りHPは{left_hp}です')
    write_hp(left_hp, filepath)
    return left_hp

def load_hp(filepath):
    with open(filepath, 'r') as f:
        hp = f.read()
    return eval(hp)

def write_hp(hp, filepath):
    with open(filepath, 'w') as f:
        f.write(str(hp))

# メイン処理 - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
if __name__ == "__main__":

    input("座標決めのためにスクリーンショットを取ります。"\
        "準備ができたらEnterキーを押してください。"\
        "Enterを押すと画面キャプチャが表示されます。"\
        "読み取りたいメッセージウィンドウの位置をマウスドラッグで選択してください。"
        )

    # 表示する画像の取得（スクリーンショット）
    img = pyautogui.screenshot()
    # スクリーンショットした画像は表示しきれないので画像リサイズ
    img_resized = img.resize(size=(int(img.width / RESIZE_RETIO),
                                   int(img.height / RESIZE_RETIO)),
                             resample=Image.BILINEAR)

    root = tkinter.Tk()
    root.attributes("-topmost", True) # tkinterウィンドウを常に最前面に表示

    # tkinterで表示できるように画像変換
    img_tk = ImageTk.PhotoImage(img_resized)

    # Canvasウィジェットの描画
    canvas1 = tkinter.Canvas(root,
                             bg="black",
                             width=img_resized.width,
                             height=img_resized.height)
    # Canvasウィジェットに取得した画像を描画
    canvas1.create_image(0, 0, image=img_tk, anchor=tkinter.NW)

    # Canvasウィジェットを配置し、各種イベントを設定
    canvas1.pack()
    canvas1.bind("<ButtonPress-1>", start_point_get)
    canvas1.bind("<Button1-Motion>", rect_drawing)
    canvas1.bind("<ButtonRelease-1>", release_action)

    root.mainloop()

    wait = 0.0
    logger.info(f'{wait}秒間隔で画面キャプチャを実行します')
    output_dir = 'output'
    fname = 'screenshot.png'
    hp_fname = 'hp.txt'
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, fname)
    hp_filepath = os.path.join(output_dir, hp_fname)
    # Define position
    x1, y1, x2, y2 = START_X, START_Y, END_X, END_Y

    init_hp = input('敵の初期HPを入力してください:')
    try:
        with open(hp_filepath, 'w') as f:
            f.write(init_hp)
        init_hp = int(init_hp)
    except ValueError as e:
        logger.error('数値を入力してください')
        raise ValueError(e)
    logger.info(f'敵の初期HPは{init_hp}です')
    logger.info('終了するには Ctrl + C を入力してください')
    prev_text = ''

    try:
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
                current_hp = calc_hp(damage, hp_filepath)
            prev_text = text
            sleep(wait)
    except KeyboardInterrupt:
        logger.info('プログラムを終了します')


