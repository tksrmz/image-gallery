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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                extension TEXT NOT NULL,
                title_id INTEGER,
                FOREIGN KEY(title_id) REFERENCES titles(id)
            )
          ''')

# Create titles table
c.execute('''
            CREATE TABLE IF NOT EXISTS titles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
          ''')

# Create tags table
c.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
          ''')

# Create image_tags table
c.execute('''
            CREATE TABLE IF NOT EXISTS image_tags (
                image_id INTEGER,
                tag_id INTEGER,
                FOREIGN KEY(image_id) REFERENCES images(id),
                FOREIGN KEY(tag_id) REFERENCES tags(id)
            )
          ''')

# Close the connection
conn.close()
