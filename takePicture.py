import time

# Taking picture script
# First create taking_picture file

open('state_files/picture_taking', 'a').close()


# Then after 2 seconds create photo file
time.sleep(2)

with open('example_files/yannno12.jpg', 'r') as f:
    content = f.read()
    with open('static/pending_pictures/yannno12.jpg', 'w') as photo:
        photo.write(content)
