__author__ = 'dvemula'

import os
import plistlib

library = plistlib.readPlist(os.path.expanduser("~/Music/iTunes/iTunes Music Library.xml"))

songs = library['Tracks']

for key in songs.iterkeys():
    song = songs[key]
    print (song['Name'])