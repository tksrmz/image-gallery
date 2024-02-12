from flask import Flask, send_from_directory, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
# from PIL import Image
import os
import math
import sqlite3
from util.load_config import load_config

PASSWORD_HASH = generate_password_hash('0008')
USERNAME = 'tk'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
IMAGES_PER_PAGE = 100

config = load_config()

app = Flask(__name__)
app.config['IMAGE_FOLDER'] = os.path.join(app.root_path, 'static/images')
app.config['DATABASE'] = os.path.join(app.root_path, config['database']['name'])
# app.config['UPLOAD_FOLDER'] = app.config['IMAGE_FOLDER']
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
    image_list = get_image_list()

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

    return render_template('image_gallery.html', image_files=image_files_to_display, total_pages=total_pages, current_page=page)

@app.route('/images/<filename>')
def send_image(filename):
    if not ('username' in session):
        return redirect(url_for('login'))

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

    return render_template('image.html', filename=filename, title=title, tag_list=tag_list)

# @app.route('/thumbnails/<filename>')
# def send_thumbnail(filename):
#     if not ('username' in session):
#         return redirect(url_for('login'))

#     return send_from_directory(app.config['THUMBNAIL_FOLDER'], filename)

# @app.route('/upload', methods=['GET', 'POST'])
# def upload_file():
#     if request.method == 'POST':
#         # Check if the post request has the file part
#         files = request.files.getlist('files')
#         # If the user does not select a file, the browser submits an
#         # empty file without a filename.
#         if not files or files[0].filename == '':
#             flash('No selected file')
#             return redirect(request.url)

#         for file in files:
#             if file and allowed_file(file.filename):
#                 filename = secure_filename(file.filename)
#                 file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

#                 # Check if file already exists
#                 if os.path.exists(file_path):
#                     flash(f'File already exists: {filename}')
#                     continue # Skip saving this file and continue with the next one

#                 file.save(file_path)
#                 thumbnail_path = os.path.join(app.config['THUMBNAIL_FOLDER'], filename)
#                 create_thumbnail(file_path, thumbnail_path)

#         flash('File(s) successfully uploaded and thumbnails created')
#         return redirect(url_for('upload_file'))

#     if not ('username' in session):
#         return redirect(url_for('login'))

#     return render_template('upload.html')

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

def get_image_list():
    # get image list from sqlite3
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    c.execute('''SELECT name FROM images''')
    image_list = [row[0] for row in c.fetchall()]
    conn.close()
    return image_list

if __name__ == '__main__':
    app.run(debug=True)
