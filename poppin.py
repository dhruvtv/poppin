__author__ = 'dvemula'

import os
import plistlib
import sqlite3
import time

DEFAULT_PATH = "~/Music/iTunes/iTunes Music Library.xml"

def get_itunes_songs(path=DEFAULT_PATH):
    library = plistlib.readPlist(os.path.expanduser(path))
    return library['Tracks']

def get_database_connection(location):
    try:
        return sqlite3.connect(location)
    except sqlite3.Error, e:
        print "Error: %s" % e.args[0]

# Unix Timestamp is the time elapsed after Jan 1, 1970 UTC
# Apple Timestamp is the time elapsed after Jan 1, 1904 local time (!)
def get_apple_unix_timestamp_diff():
    # diff(Jan 1, 1970 UTC, Jan 1, 1904 UTC) = 2082844800
    UTC_EPOCH_DIFF = 2082844800

    #UTC - local time difference (considering daylight savings)
    def utc_local_diff():
        if time.daylight > 0:
            return time.altzone
        else:
            return time.timezone

    # diff = Epoch diff minus local-UTC diff
    return UTC_EPOCH_DIFF - utc_local_diff()

def get_apple_timestamp(unix_timestamp):
    return unix_timestamp + get_apple_unix_timestamp_diff()

def get_unix_timestamp(apple_timestamp):
    return apple_timestamp - get_apple_unix_timestamp_diff()

def is_new(cursor):
    table_count = cursor.execute("SELECT COUNT(NAME) "
                                 "FROM SQLITE_MASTER")
    return table_count.fetchone()[0] == 0

def init_database(cursor):
    cursor.execute("CREATE TABLE Snapshots("
                   "Id INTEGER PRIMARY KEY, "
                   "Time INTEGER)")
    cursor.execute("CREATE TABLE Deltas("
                   "Key INTEGER, "
                   "Delta INTEGER,"
                   "Snapshot INTEGER,"
                   "FOREIGN KEY (Snapshot) REFERENCES Snapshots(Id))")

def init_deltas(cursor, songs, timestamp):
    cursor.execute("INSERT INTO Snapshots("
                   "Time) VALUES(?)", (timestamp,))
    snapshot_id = cursor.lastrowid
    deltas = []
    for key in songs.iterkeys():
        song = songs[key]
        if song.has_key('Play Count'):
            deltas.append((key, song['Play Count'], snapshot_id))
    cursor.executemany("INSERT INTO Deltas("
                       "Key, Delta, Snapshot) "
                       "VALUES(?, ?, ?)", deltas)

def update_deltas(cursor, songs, timestamp):
    cursor.execute("SELECT * FROM Snapshots WHERE Id = "
                   "(SELECT MAX(Id) FROM Snapshots)")
    prev_snapshot = cursor.fetchone()

    deltas = dict()
    for key in songs.iterkeys():
        song = songs[key]
        if song.has_key('Play Count') and song['Play Date'] > prev_snapshot[1]:
            deltas[key] = (key, song['Play Count'], 0)

    if len(deltas) > 0:
        cursor.execute("SELECT Key, SUM(Delta) FROM Deltas "
                       "WHERE Key IN %s "
                       "GROUP BY Key" % str(tuple(deltas.iterkeys())))
        new_songs = cursor.fetchall()

        cursor.execute("INSERT INTO Snapshots(Time) VALUES(?)", (timestamp,))
        snapshot = cursor.lastrowid

        for new_song in new_songs:
            key = str(new_song[0])
            deltas[key] = (key, deltas[key][1] - new_song[1], snapshot)

        cursor.executemany("INSERT INTO Deltas("
                           "Key, Delta, Snapshot)"
                           " VALUES(?, ?, ?)", deltas.itervalues())
    else:
        print "No new ones"

#unix_time = time.time()
#print "Unix time:", unix_time
#print "Apple time:", get_apple_timestamp(time.time())

def main():
    songs = get_itunes_songs()
    conn = get_database_connection('poppin.sqlite')
    timestamp = int(get_apple_timestamp(time.time()))
    with conn:
        cursor = conn.cursor()
        if is_new(cursor):
            init_database(cursor)
            init_deltas(cursor, songs, timestamp)
        else:
            update_deltas(cursor, songs, timestamp)

def get_latest_snapshot():
    songs = get_itunes_songs()
    conn = get_database_connection('poppin.sqlite')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Deltas WHERE Snapshot = "
                   "(SELECT MAX(Id) FROM Snapshots)")
    new_songs = cursor.fetchall()

    for new_song in new_songs:
        key = str(new_song[0])
        print songs[key]['Name'], new_song[1], new_song[2]

get_latest_snapshot()