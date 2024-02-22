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

    # Get query parameters
    page = request.args.get('page', 1, type=int)
    selected_tag_list = request.args.getlist('tag')
    filter_type = request.args.get('filter_type', 'and')

    # Get image list displayed on the page
    if len(selected_tag_list) > 0 and filter_type == 'and':
        image_list = get_image_list_and(selected_tag_list)
    elif len(selected_tag_list) > 0 and filter_type == 'or':
        image_list = get_image_list_or(selected_tag_list)
    else:
        # Get all image if no tag is selected or filter type is something but expected
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

    return render_template('image_gallery.html', image_files=image_files_to_display, total_pages=total_pages, current_page=page, selected_tag_list=selected_tag_list, all_tag_list=get_tag_list(), filter_type=filter_type)

@app.route('/images/<filename>')
def send_image(filename):
    if not ('username' in session):
        return redirect(url_for('login'))

    attached_tag_list = get_tags_attached_to_image(filename)
    all_tag_list = get_tag_list()

    return render_template('image.html', filename=filename, attached_tag_list=attached_tag_list, all_tag_list=all_tag_list)

# @app.route('/thumbnails/<filename>')
# def send_thumbnail(filename):
#     if not ('username' in session):
#         return redirect(url_for('login'))

#     return send_from_directory(app.config['THUMBNAIL_FOLDER'], filename)

@app.route('/images/<filename>/tags', methods=['POST'])
def update_tags_on_image(filename):
    if not ('username' in session):
        return redirect(url_for('login'))

    sent_tag_list = request.form.getlist('tag')
    attached_tag_list = get_tags_attached_to_image(filename)

    inserted_tag_set = set(sent_tag_list) - set(attached_tag_list)
    attach_tag_to_image(inserted_tag_set, filename)

    deleted_tag_set = set(attached_tag_list) - set(sent_tag_list)
    detach_tag_from_image(deleted_tag_set, filename)

    return redirect(url_for('send_image', filename=filename))

@app.route('/tags', methods=['GET', 'POST'])
def show_tags():
    if not ('username' in session):
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Get request param
        tag = request.form['tag']
        try:
            create_tag(tag)
        except sqlite3.IntegrityError:
            flash(f'Tag already exists: {tag}')
        else:
            flash(f'Tag successfully created: {tag}')
        return redirect(url_for('show_tags'))

    return render_template('tags.html', all_tag_list=get_tag_list())

@app.route('/tags/<tagname>', methods=['POST'])
def update_tag(tagname):
    if not ('username' in session):
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Get request param
        new_name = request.form['newname']
        # Rename tag
        try:
            update_tag_name(tagname, new_name)
        except sqlite3.IntegrityError:
            flash(f'Tag already exists. Nothing updated: {new_name}')
        except ValueError as err:
            flash(f'Error: {str(err)}: {tagname}', 'error')
        else:
            flash(f'Tag successfully renamed: {tagname} -> {new_name}')

        return redirect(url_for('show_tags'))
    else:
        return redirect(url_for('show_tags'))

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

    with conn:
        # images.id is an alias for rowid as images.id is an INTEGER PRIMARY KEY
        #
        # > if a rowid table has a primary key that consists of a single column and the declared
        # type of that column is "INTEGER" in any mixture of upper and lower case, then the column
        # becomes an alias for the rowid.
        # https://www.sqlite.org/lang_createtable.html#rowids_and_the_integer_primary_key

        # name will not conflict as timestamp is used as filename so try-except is not necessary
        image_id = conn.execute('''
                    INSERT INTO images (name)
                    VALUES (?)
                ''', (filename,)).lastrowid

        # Uniqueness of hash is checked before this function is called so try-except is not necessary
        conn.execute('''
                    INSERT INTO hashes (hash, image_id)
                    VALUES (?, ?)
                ''', (hash, image_id))
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
    result = conn.execute('''
                SELECT id
                FROM hashes
                WHERE hash = ?
            ''', (hash,)).fetchone()
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

def get_image_list():
    conn = sqlite3.connect(app.config['DATABASE'])
    result = conn.execute('SELECT name FROM images').fetchall()
    conn.close()
    return [row[0] for row in result]

def get_image_list_or(tag_list):
    conn = sqlite3.connect(app.config['DATABASE'])
    result = conn.execute(f'''
            SELECT DISTINCT i.name
            FROM images AS i
            JOIN image_tags AS it
                ON i.id = it.image_id
            JOIN tags AS tg
                ON it.tag_id = tg.id
            WHERE tg.name IN ({','.join(['?'] * len(tag_list))})
        ''', tuple(tag_list)).fetchall()
    conn.close()
    return [row[0] for row in result]

def get_image_list_and(tag_list):
    conn = sqlite3.connect(app.config['DATABASE'])
    result = conn.execute(f'''
            SELECT i.name
            FROM images AS i
            JOIN image_tags AS it
                ON i.id = it.image_id
            JOIN tags AS tg
                ON it.tag_id = tg.id
            WHERE tg.name IN ({','.join(['?'] * len(tag_list))})
            GROUP BY i.name
            HAVING COUNT(DISTINCT tg.name) = ?
        ''', tuple(tag_list + [len(tag_list)])).fetchall()
    conn.close()
    return [row[0] for row in result]

def get_tags_attached_to_image(filename):
    # Read file info from sqlite3
    conn = sqlite3.connect(app.config['DATABASE'])
    query_result = conn.execute('''
                SELECT t.name
                FROM tags AS t
                JOIN image_tags AS it
                    ON t.id = it.tag_id
                JOIN images AS i
                    ON it.image_id = i.id
                WHERE i.name = ?
            ''', (filename,)).fetchall()
    tag_list = [row[0] for row in query_result]
    conn.close()
    return tag_list

def get_tag_list():
    conn = sqlite3.connect(app.config['DATABASE'])
    tag_list = [row[0] for row in conn.execute('SELECT name FROM tags').fetchall()]
    conn.close()
    return tag_list

def create_tag(tag):
    conn = sqlite3.connect(app.config['DATABASE'])
    try:
        with conn:
            conn.execute('INSERT INTO tags (name) VALUES (?)', (tag,))
    except sqlite3.IntegrityError:
        raise
    finally:
        conn.close()

def update_tag_name(current, new):
    conn = sqlite3.connect(app.config['DATABASE'])
    try:
        with conn:
            match conn.execute('''
                        UPDATE tags SET name = ? WHERE name = ?
                    ''', (new, current)).rowcount:
                # Can't update the target tag
                case 0: raise ValueError('No tag found')
                # Normal case
                case 1: pass
                # Multiple tags found
                case _: raise ValueError('Multiple tags found')
    except sqlite3.IntegrityError:
        raise
    except ValueError:
        raise
    finally:
        conn.close()

def attach_tag_to_image(tag_list, filename):
    conn = sqlite3.connect(app.config['DATABASE'])
    # tag_list is a list of tags to attach to the image
    # and tags in tag_list is not attached to the image yet
    # so no need to add try-except for IntegrityError
    with conn:
        conn.executemany('''
                    INSERT INTO image_tags (image_id, tag_id)
                    SELECT
                        (SELECT id FROM images WHERE name = ?),
                        (SELECT id FROM tags WHERE name = ?)
                ''', [(filename, tag) for tag in tag_list])
    conn.close()

def detach_tag_from_image(tag_list, filename):
    conn = sqlite3.connect(app.config['DATABASE'])
    with conn:
        conn.executemany('''
                    DELETE FROM image_tags
                    WHERE image_id = (SELECT id FROM images WHERE name = ?)
                    AND tag_id = (SELECT id FROM tags WHERE name = ?)
                ''', [(filename, tag) for tag in tag_list])
    conn.close()

def execute_script_from_file(filename):
    conn = sqlite3.connect(app.config['DATABASE'])
    with open(filename, 'r') as f:
        sql = f.read()
        with conn:
            conn.executescript(sql)
    conn.close()

# Setup for dummy mode
if os.environ.get('DATA_SOURCE', '') == 'dummy':
    app.logger.info('Using dummy database')
    # Execute script to drop tables then create tables
    execute_script_from_file('sql/drop_tables.sql')
    execute_script_from_file('sql/create_tables.sql')

if __name__ == '__main__':
    # Code in this block will only be executed if this file is run directly (python app.py)
    # It will not be executed if this file is imported as a module (flask run)
    app.logger.info('App is executing directly')

    app.run(debug=True)
