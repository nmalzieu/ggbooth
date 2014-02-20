import glob
import os

# Checking pending pictures folder
pending_pictures = filter(os.path.isfile, glob.glob('static/pending_pictures/*.jpg'))
pending_pictures.sort(key=lambda x: os.path.getmtime(x))

last_pending_picture = pending_pictures[-1]

# Move last picture to printing picture folder
filename = last_pending_picture.split('/')[-1]
dest = 'printing_pictures/%s' % filename
os.rename(last_pending_picture, dest)
