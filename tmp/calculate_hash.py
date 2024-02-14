# Calculates the hash of a file

import hashlib
import os
import sqlite3

def get_file_list_from_sqlite3():
    # Connect to database
    conn = sqlite3.connect('../image_gallery.sqlite3')
    c = conn.cursor()

    # Get file list from sqlite3
    c.execute('''
                SELECT name
                FROM images
            ''')
    file_list = [row[0] for row in c.fetchall()]
    conn.close()
    return file_list

def calculate_hash(filename):
    full_filename = os.path.join('../static/images', filename)
    # Calculate the hash of a file
    BLOCKSIZE = 65536
    hasher = hashlib.md5()
    with open(full_filename, 'rb') as afile:
        buf = afile.read(BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(BLOCKSIZE)
    return hasher.hexdigest()

def insert_hash_into_sqlite3(file, hash):
    # Connect to database
    conn = sqlite3.connect('../image_gallery.sqlite3')
    c = conn.cursor()

    # Insert hash into sqlite3
    c.execute('''
                INSERT INTO hashes (hash, image_name)
                VALUES (?, ?)
            ''', (hash, file))
    conn.commit()
    conn.close()

def main():
    # Get file list from sqlite3
    file_list = get_file_list_from_sqlite3()

    # Calculate hash and insert into sqlite3
    hash_set = set()
    for file in file_list:
        hash = calculate_hash(file)
        if hash in hash_set:
            print(f'Duplicate hash: {hash}, file: {file}')
            continue
        hash_set.add(hash)
        insert_hash_into_sqlite3(file, hash)

if __name__ == '__main__':
    main()
