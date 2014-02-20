import glob
import os
import json
import time
import subprocess

from flask import Flask
from flask import render_template
from PIL import Image

app = Flask(__name__)
app.debug = True

global printing_time
printing_time = 56  # From reviews, printing takes 56 seconds
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
        resize_and_crop(last_picture, last_picture, (600, 800))

    if picture_taking:
        state = 1
        response = json.dumps(
            {
                'state': 1
            }
        )
    elif pending_pictures:
        # Pending: showing picture
        # if red or green, change state
        state = 2
        response = json.dumps(
            {
                'state': 2,
                'last_picture': pending_pictures[-1]
            }
        )
        if is_there_green_and_red():
            # Do nothing
            pass
        elif is_there_green():
            # Print picture
            print "PRINTING LAST PICTURE"
            last_picture = pending_pictures[-1]
            last_picture_name = last_picture.split('/')[-1]
            printing_picture_path = 'printing_pictures/%s' % last_picture_name
            os.rename(last_picture, printing_picture_path)
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
                'state': 3
            }
        )
    else:
        state = 0
        response = json.dumps(
            {
                'state': 0
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


def resize_and_crop(img_path, modified_path, size, crop_type='middle'):
    """
    Resize and crop an image to fit the specified size.

    args:
        img_path: path for the image to resize.
        modified_path: path to store the modified image.
        size: `(width, height)` tuple.
        crop_type: can be 'top', 'middle' or 'bottom', depending on this
            value, the image will cropped getting the 'top/left', 'middle' or
            'bottom/right' of the image to fit the size.
    raises:
        Exception: if can not open the file in img_path of there is problems
            to save the image.
        ValueError: if an invalid `crop_type` is provided.
    """
    # If height is higher we resize vertically, if not we resize horizontally
    img = Image.open(img_path)
    # Get current and desired ratio for the images
    img_ratio = img.size[0] / float(img.size[1])
    ratio = size[0] / float(size[1])
    #The image is scaled/cropped vertically or horizontally depending on the ratio
    if ratio > img_ratio:
        img = img.resize((size[0], round(size[0] * img.size[1] / img.size[0])),
                Image.ANTIALIAS)
        # Crop in the top, middle or bottom
        if crop_type == 'top':
            box = (0, 0, img.size[0], size[1])
        elif crop_type == 'middle':
            box = (0, round((img.size[1] - size[1]) / 2), img.size[0],
                   round((img.size[1] + size[1]) / 2))
        elif crop_type == 'bottom':
            box = (0, img.size[1] - size[1], img.size[0], img.size[1])
        else :
            raise ValueError('ERROR: invalid value for crop_type')
        img = img.crop(box)
    elif ratio < img_ratio:
        img = img.resize((round(size[1] * img.size[0] / img.size[1]), size[1]),
                Image.ANTIALIAS)
        # Crop in the top, middle or bottom
        if crop_type == 'top':
            box = (0, 0, size[0], img.size[1])
        elif crop_type == 'middle':
            box = (round((img.size[0] - size[0]) / 2), 0,
                   round((img.size[0] + size[0]) / 2), img.size[1])
        elif crop_type == 'bottom':
            box = (img.size[0] - size[0], 0, img.size[0], img.size[1])
        else :
            raise ValueError('ERROR: invalid value for crop_type')
        img = img.crop(box)
    else :
        img = img.resize((size[0], size[1]),
                Image.ANTIALIAS)
        # If the scale is the same, we do not need to crop
    img.save(modified_path)
