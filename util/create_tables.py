import sqlite3
from util.load_config import load_config

# Load configuration
CONFIG = load_config()

# Connect to database
conn = sqlite3.connect(CONFIG['database']['name'])
c = conn.cursor()

# Create images table
c.execute('''
            CREATE TABLE IF NOT EXISTS images (
                name TEXT PRIMARY KEY NOT NULL,
                extension TEXT NOT NULL,
                title_name TEXT,
                FOREIGN KEY(title_name) REFERENCES titles(name)
            )
          ''')

# Create titles table
c.execute('''
            CREATE TABLE IF NOT EXISTS titles (
                name TEXT PRIMARY KEY NOT NULL
            )
          ''')

# Create tags table
c.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                name TEXT PRIMARY KEY NOT NULL
            )
          ''')

# Create image_tags table
c.execute('''
            CREATE TABLE IF NOT EXISTS image_tags (
                image_name TEXT NOT NULL,
                tag_name TEXT NOT NULL,
                FOREIGN KEY(image_name) REFERENCES images(name),
                FOREIGN KEY(tag_name) REFERENCES tags(name)
            )
          ''')

# Create hash table
c.execute('''
            CREATE TABLE IF NOT EXISTS hashes (
                hash TEXT PRIMARY KEY,
                image_name TEXT NOT NULL,
                FOREIGN KEY(image_name) REFERENCES images(name)
            )
          ''')

# Close the connection
conn.close()
