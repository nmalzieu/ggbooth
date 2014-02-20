import glob
import os
import json
import time
import subprocess

from flask import Flask
from flask import render_template

app = Flask(__name__)
app.debug = True

global printing_time
printing_time = 65  # From reviews, printing takes 56 seconds
global last_printing_beginning
global state

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


@app.route('/')
def home():
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
    # Checking pending pictures folder
    pending_pictures = filter(os.path.isfile, glob.glob('static/pending_pictures/*.jpg'))
    pending_pictures.sort(key=lambda x: os.path.getmtime(x))

    # Checking printing pictures folder
    printing_pictures = filter(os.path.isfile, glob.glob('printing_pictures/*.jpg'))
    printing_pictures.sort(key=lambda x: os.path.getmtime(x))

    # Checking state files
    picture_taking = len(glob.glob('state_files/picture_taking'))

    response = ''

    if pending_pictures and picture_taking:
        # Picture taken! we can remove picture_taking file and resize image
        os.remove('state_files/picture_taking')
        picture_taking = 0
        last_picture = pending_pictures[-1]

    if picture_taking:
        state = 1
        response = json.dumps(
            {
                'state': 1,
                'html': render_template('taking_picture.html')
            }
        )
    elif pending_pictures:
        # Pending: showing picture
        # if red or green, change state
        state = 2
        response = json.dumps(
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
        response = json.dumps(
            {
                'state': 3,
                'html': render_template('printing.html')
            }
        )
    else:
        state = 0
        response = json.dumps(
            {
                'state': 0,
                'html': render_template('ready.html')
            }
        )
        if is_there_green_and_red():
            pass
        elif is_there_green():
            # Let's take a picture!!
            open('state_files/picture_taking', 'a').close()
            timestamp = time.time()
            filename_arg = '--filename=%s.jpg' % timestamp
            subprocess.Popen(['gphoto2', filename_arg, '--capture-image-and-download'], cwd='static/pending_pictures/')

    clean_red_green()
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
