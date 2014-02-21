import glob
import os
import json
import time
import subprocess
import threading
from PIL import Image

from flask import Flask
from flask import render_template

app = Flask(__name__)
app.debug = True

global printing_time
printing_time = 65  # From reviews, printing takes 56 seconds
global last_printing_beginning
global state
global wat
global photo_timer
global photo_timer_duration
photo_timer_duration = 5
photo_timer = 0
wat = Image.open('static/images/watermark.png')

global count

global booth_error
booth_error = False

state = 0


def is_there_red():
    return os.path.isfile('red')


def is_there_green():
    return os.path.isfile('green')


def is_there_green_and_red():
    return os.path.isfile('green') and os.path.isfile('red')


def clean_red_green():
    if is_there_red():
        os.remove('red')
    if is_there_green():
        os.remove('green')


def set_count(count):
    with open('count.txt', 'w') as countfile:
        countfile.write(str(count))


def watermark(im, mark, position, opacity=1):
    """Adds a watermark to an image."""
    if im.mode != 'RGBA':
        im = im.convert('RGBA')
    # create a transparent layer the size of the image and draw the
    # watermark in that layer.
    layer = Image.new('RGBA', im.size, (0, 0, 0, 0))
    if position == 'tile':
        for y in range(0, im.size[1], mark.size[1]):
            for x in range(0, im.size[0], mark.size[0]):
                layer.paste(mark, (x, y))
    elif position == 'scale':
        # scale, but preserve the aspect ratio
        ratio = min(
            float(im.size[0]) / mark.size[0], float(im.size[1]) / mark.size[1])
        w = int(mark.size[0] * ratio)
        h = int(mark.size[1] * ratio)
        mark = mark.resize((w, h))
        layer.paste(mark, ((im.size[0] - w) / 2, (im.size[1] - h) / 2))
    else:
        layer.paste(mark, position)
    # composite the watermark with the layer
    return Image.composite(layer, im, layer)


def asyncPictureDone(booth_errorCode):
    global booth_error
    if booth_errorCode:
        print "ASYNC PICTURE DONE WITH ERRORS"
        booth_error = True


def asyncPicture(onExit, filename_arg):
    """
    Runs the given args in a subprocess.Popen, and then calls the function
    onExit when the subprocess completes.
    onExit is a callable object,and popenArgs is a list/tuple of args that
    would give to subprocess.Popen.
    """
    def runInThread(onExit, filename_arg):
        photoProcess = subprocess.Popen(['gphoto2', filename_arg, '--capture-image-and-download'], cwd='static/pending_pictures/')
        # wait for the process to terminate
        out, err = photoProcess.communicate()
        errcode = photoProcess.returncode
        onExit(errcode)
        return
    thread = threading.Thread(target=runInThread, args=(onExit, filename_arg))
    thread.start()
    # returns immediately after the thread starts
    return thread


def takePicture():
    # Let's take a picture!!
    timestamp = time.time()
    filename_arg = '--filename=%s.jpg' % timestamp
    asyncPicture(asyncPictureDone, filename_arg)

def notifyPicture():
    open('state_files/picture_taking', 'a').close()


@app.route('/')
def home():
    global booth_error
    booth_error = False
    clean_red_green()
    picture_taking = len(glob.glob('state_files/picture_taking'))
    if picture_taking:
        os.remove('state_files/picture_taking')
    subprocess.Popen(['killall', 'PTPCamera'])
    return render_template('home.html')


@app.route('/state/')
def ready():
    global state
    global printing_time
    global last_printing_beginning
    global wat
    global count
    global photo_timer
    global photo_timer_duration
    global booth_error

    if booth_error:
        state = -1
        json_response = json.dumps({
            'state': -1,
            'html': render_template('error.html')
        })
    else:
        with open('count.txt', 'r') as countfile:
            count = int(countfile.read())

        # Checking pending pictures folder
        pending_pictures = filter(os.path.isfile, glob.glob('static/pending_pictures/*.jpg'))
        pending_pictures.sort(key=lambda x: os.path.getmtime(x))

        # Checking printing pictures folder
        printing_pictures = filter(os.path.isfile, glob.glob('printing_pictures/*.jpg'))
        printing_pictures.sort(key=lambda x: os.path.getmtime(x))

        # Checking state files
        picture_taking = len(glob.glob('state_files/picture_taking'))

        json_response = ''

        if pending_pictures and picture_taking:
            # Picture taken! we can remove picture_taking file and resize image
            os.remove('state_files/picture_taking')
            picture_taking = 0
            last_picture = pending_pictures[-1]

        if picture_taking:
            state = 1
            json_response = json.dumps(
                {
                    'state': 1,
                    'html': render_template('taking_picture.html')
                }
            )
        elif pending_pictures:
            # Pending: showing picture
            # if red or green, change state
            if state != 2:
                # Picture was JUST taken, let's apply watermark
                with open(pending_pictures[-1], 'rb') as im:
                    print pending_pictures[-1]
                    image = Image.open(im)
                    im_watermarked = watermark(image, wat, (2150, 1300))
                    im_watermarked.save(pending_pictures[-1])
                    del im_watermarked
                    del image
            state = 2
            json_response = json.dumps(
                {
                    'state': 2,
                    'html': render_template('last_picture.html', last_picture_url=pending_pictures[-1])
                }
            )
            if is_there_green_and_red():
                # Do nothing
                pass
            elif is_there_green():
                # Print picture
                if len(pending_pictures) == 1:
                    print "PRINTING LAST PICTURE"
                    last_picture = pending_pictures[-1]
                    last_picture_name = last_picture.split('/')[-1]
                    printing_picture_path = 'printing_pictures/%s' % last_picture_name
                    os.rename(last_picture, printing_picture_path)
                    subprocess.Popen(['lp', '-o', 'media=Postcard(4x6in)', '-o', 'landscape', printing_picture_path])
                    # Print process sent: let's reduce count so we know when there is no more paper
                    set_count(count - 1)
            elif is_there_red():
                # Cancel, not printing, archiving
                print "ARCHIVING PICTURE"
                last_picture = pending_pictures[-1]
                last_picture_name = last_picture.split('/')[-1]
                archived_picture_path = 'archived_pictures/%s' % last_picture_name
                os.rename(last_picture, archived_picture_path)
        elif printing_pictures:
            # After printing time, picture is not printing,
            # it's printed
            if state != 3:
                # last state was not printing!
                last_printing_beginning = time.time()
            if state == 3:
                # last state was already printed
                # printing has finished after printing_time
                if time.time() - last_printing_beginning > printing_time:
                    src = printing_pictures[-1]
                    filename = src.split('/')[-1]
                    dest = 'printed_pictures/%s' % filename
                    os.rename(src, dest)
            state = 3
            json_response = json.dumps(
                {
                    'state': 3,
                    'html': render_template('printing.html')
                }
            )
        else:
            if count > 3:
                if state != 5:
                    state = 0
                    json_response = json.dumps(
                        {
                            'state': 0,
                            'html': render_template('ready.html')
                        }
                    )
                else:
                    # We're in timer mode
                    if time.time() - photo_timer >= photo_timer_duration:
                        notifyPicture()
                    elif time.time() - photo_timer >= photo_timer_duration - 1:
                        takePicture()
                    json_response = json.dumps(
                        {
                            'state': 5,
                            'html': render_template('picture_timer.html', timer=max(1, photo_timer_duration - int(time.time() - photo_timer)))
                        }
                    )
                if is_there_green_and_red():
                    pass
                elif is_there_green():
                    state = 5
                    json_response = json.dumps(
                        {
                            'state': 5,
                            'html': render_template('picture_timer.html', timer=5)
                        }
                    )
                    photo_timer = time.time()
            else:
                state = 4
                json_response = json.dumps(
                    {
                        'state': 4,
                        'html': render_template('nopaper.html')
                    }
                )

    clean_red_green()
    return json_response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
