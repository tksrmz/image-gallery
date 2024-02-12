# Move data from Redis to SQLite3

import sqlite3
import redis
import logging

logging.basicConfig(filename='insert.log',
                    filemode='w',
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

r = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

# Connect to database
conn = sqlite3.connect('../image_gallery.sqlite3')
c = conn.cursor()


def get_image_data(key):
    name = r.hget(key, 'name')
    extension = r.hget(key, 'extension')
    title = r.hget(key, 'title')
    tag_list = []
    for itr in r.hscan_iter(key, 'tag:*'):
        tag_list.append(r.hget(key, itr[0]))
    return name, extension, title, tag_list

count = 0
when_to_commit = 1000

for key in r.keys('image:*'):
    # Don't insert 'image:1'
    if key == 'image:1':
        logging.info('Skipping image:1')
        continue

    # Get the image data
    name, extension, title, tag_list = get_image_data(key)

    # Insert the title
    if title:
        c.execute('''
                    INSERT INTO titles (name)
                    VALUES (?)
                ''', (title,))
    else:
        logging.info(f'No title for image: {name}')
    title_id = c.lastrowid if title else None

    # Insert the image
    c.execute('''
                INSERT INTO images (name, extension, title_id)
                VALUES (?, ?, ?)
              ''', (name, extension, title_id))
    image_id = c.lastrowid

    # Insert the tags
    if tag_list:
        c.executemany('''
                        INSERT INTO tags (name)
                        VALUES (?)
                    ''', [(tag,) for tag in tag_list])
    else:
        logging.info(f'No tags for image: {name}')

    # Insert the image_tags
    for tag in tag_list:
        c.execute('''
                    INSERT INTO image_tags (image_id, tag_id)
                    VALUES (?, (SELECT id FROM tags WHERE name = ?))
                  ''', (image_id, tag))

    count += 1
    if count % when_to_commit == 0:
        logging.info(f'Committing {when_to_commit} records')
        conn.commit()
        count = 0

# Commit the changes
conn.commit()

# Close the connection
conn.close()
