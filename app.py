import hashlib
from flask import Flask, render_template, request, redirect, url_for, flash, session
import werkzeug
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
# from PIL import Image
import os
import math
import sqlite3
from datetime import datetime

PASSWORD_HASH = generate_password_hash('0008')
USERNAME = 'tk'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
IMAGES_PER_PAGE = 100

app = Flask(__name__)
app.config.from_envvar('IMAGE_GALLERY_ENV_SETTINGS')
app.config['IMAGE_FOLDER'] = os.path.join(app.root_path, 'static/images')
# app.config['THUMBNAIL_FOLDER'] = os.path.join(app.root_path, 'thumbnails')
app.secret_key = 'my_secret_key'

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == USERNAME and check_password_hash(PASSWORD_HASH, password):
            session['username'] = username
            return redirect(url_for('show_images'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/')
def show_images():
    if not ('username' in session):
        return redirect(url_for('login'))

    page = request.args.get('page', 1, type=int)
    title = request.args.get('title')
    tag = request.args.get('tag')
    image_list = get_image_list(title, tag)

    # # Ensure thumbnails exist for all images
    # for image in image_files:
    #     original_path = os.path.join(app.config['IMAGE_FOLDER'], image)
    #     thumbnail_path = os.path.join(app.config['THUMBNAIL_FOLDER'], image)
    #     if not os.path.exists(thumbnail_path):
    #         create_thumbnail(original_path, thumbnail_path)

    # Pagenation calculations
    total_images = len(image_list)
    total_pages = math.ceil(total_images / IMAGES_PER_PAGE)
    start = (page - 1) * IMAGES_PER_PAGE
    end = start + IMAGES_PER_PAGE
    image_files_to_display = image_list[start:end]

    return render_template('image_gallery.html', image_files=image_files_to_display, total_pages=total_pages, current_page=page, title=title, tag=tag)

@app.route('/images/<filename>')
def send_image(filename):
    if not ('username' in session):
        return redirect(url_for('login'))

    title, tag_list = get_image_info(filename)
    return render_template('image.html', filename=filename, title=title, tag_list=tag_list)

# @app.route('/thumbnails/<filename>')
# def send_thumbnail(filename):
#     if not ('username' in session):
#         return redirect(url_for('login'))

#     return send_from_directory(app.config['THUMBNAIL_FOLDER'], filename)

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if not ('username' in session):
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file:
            filename = secure_filename(file.filename)
            new_filename = datetime.now().strftime('%Y%m%d%H%M%S%f') + os.path.splitext(filename)[1]
            file_path = os.path.join(app.config['IMAGE_FOLDER'], new_filename)

            # Check if file already exists (name collision)
            if os.path.exists(file_path):
                flash(f'File already exists(name collision): {filename}')
                return redirect(request.url)

            # Check if file already exists (hash collision)
            hash = calculate_hash(file)
            if exists_same_hash(hash):
                flash(f'File already exists(hash collision): {filename}')
                return redirect(request.url)

            insert_file_data(new_filename, hash)
            # Save file only after db is updated
            file.save(file_path)
            # thumbnail_path = os.path.join(app.config['THUMBNAIL_FOLDER'], filename)
            # create_thumbnail(file_path, thumbnail_path)

            flash(f'File successfully uploaded: {new_filename}')
            return redirect(url_for('upload_file'))

    return render_template('upload.html')

def insert_file_data(filename, hash):
    # Insert file data into sqlite3
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    c.execute('''
                INSERT INTO images (name)
                VALUES (?)
            ''', (filename,))
    image_id = c.lastrowid
    c.execute('''
                INSERT INTO hashes (hash, image_id)
                VALUES (?, ?)
            ''', (hash, image_id))
    conn.commit()
    conn.close()

def calculate_hash(file: werkzeug.datastructures.FileStorage):
    BLOCKSIZE = 65536
    hasher = hashlib.md5()
    buf = file.read(BLOCKSIZE)
    while len(buf) > 0:
        hasher.update(buf)
        buf = file.read(BLOCKSIZE)
    # Reset file pointer to the beginning so that the file can be read again
    file.seek(0)
    return hasher.hexdigest()

def exists_same_hash(hash):
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    c.execute('''
                SELECT id
                FROM hashes
                WHERE hash = ?
            ''', (hash,))
    result = c.fetchone()
    conn.close()

    # Return True if hash exists, False otherwise
    return result != None

# def create_thumbnail(image_path, thumbnail_path, size=(100, 100)):
#     """Create a thumbnail for an image.

#     :param image_path: Path to the original image.
#     :param thumbnail_path: Path to save the thumbnail.
#     :param size: A tuple (width, height) for the thumbnail size.
#     """
#     with Image.open(image_path) as img:
#         img.thumbnail(size)
#         img.save(thumbnail_path)

# def allowed_file(filename):
#     return '.' in filename and \
#             filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_image_list(title, tag):
    # Change query based on title and tag
    if title and tag:
        query = '''
                    SELECT i.name
                    FROM images AS i
                    JOIN titles AS t
                      ON i.title_id = t.id
                    JOIN image_tags AS it
                      ON i.id = it.image_id
                    JOIN tags AS tg
                      ON it.tag_id = tg.id
                    WHERE t.name = ? AND tg.name = ?
                '''
        params = (title, tag)
    elif title:
        query = '''
                    SELECT i.name
                    FROM images AS i
                    JOIN titles AS t
                      ON i.title_id = t.id
                    WHERE t.name = ?
                '''
        params = (title,)
    elif tag:
        query = '''
                    SELECT i.name
                    FROM images AS i
                    JOIN image_tags AS it
                      ON i.id = it.image_id
                    JOIN tags AS tg
                      ON it.tag_id = tg.id
                    WHERE tg.name = ?
                '''
        params = (tag,)
    else:
        query = '''
                    SELECT name
                    FROM images
                '''
        params = ()

    # get image list from sqlite3
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    c.execute(query, params)
    image_list = [row[0] for row in c.fetchall()]
    conn.close()
    return image_list

def get_image_info(filename):
    # Read file info from sqlite3
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    c.execute('''
                SELECT t.name
                FROM images AS i LEFT JOIN titles AS t
                  ON i.title_id = t.id
                WHERE i.name = ?
            ''', (filename,))
    title = c.fetchone()[0]
    c.execute('''
                SELECT t.name
                FROM tags AS t
                JOIN image_tags AS it
                  ON t.id = it.tag_id
                JOIN images AS i
                  ON it.image_id = i.id
                WHERE i.name = ?
              ''', (filename,))
    tag_list = [row[0] for row in c.fetchall()]
    conn.close()
    return title, tag_list

if __name__ == '__main__':
    app.run(debug=True)
