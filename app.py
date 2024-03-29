import hashlib
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, session, g, send_file
import werkzeug
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
# from PIL import Image
import os
import math
import sqlite3
from datetime import datetime
import zipfile
from io import BytesIO

PASSWORD_HASH = generate_password_hash('0008')
USERNAME = 'tk'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
IMAGES_PER_PAGE = 100

app = Flask(__name__)
app.config.from_envvar('IMAGE_GALLERY_ENV_SETTINGS')
app.config['IMAGE_FOLDER'] = os.path.join(app.root_path, 'static/images')
# app.config['THUMBNAIL_FOLDER'] = os.path.join(app.root_path, 'thumbnails')
app.secret_key = 'my_secret_key'

def get_db():
    if 'db' not in g:
        # Establish a new connection
        g.db = sqlite3.connect(app.config['DATABASE'])
        # Enable foreign key constraints
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db

@app.teardown_request
def close_db_on_g(exception=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

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

    # Get image list
    image_list = service_get_image_list(selected_tag_list, filter_type)

    # Get all tags
    all_tag_list = get_tag_list()

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

    return render_template('image_gallery.html', image_files=image_files_to_display, total_pages=total_pages, current_page=page, selected_tag_list=selected_tag_list, all_tag_list=all_tag_list, filter_type=filter_type)

@app.route('/recent-images')
def show_recent_images():
    if not ('username' in session):
        return redirect(url_for('login'))

    # Get query parameters
    page = request.args.get('page', 1, type=int)

    # Get all image if no tag is selected or filter type is something but expected
    image_list = get_image_list_recent()

    # Pagenation calculations
    total_images = len(image_list)
    total_pages = math.ceil(total_images / IMAGES_PER_PAGE)
    start = (page - 1) * IMAGES_PER_PAGE
    end = start + IMAGES_PER_PAGE
    image_files_to_display = image_list[start:end]

    return render_template('recent_image_gallery.html', image_files=image_files_to_display, total_pages=total_pages, current_page=page)

@app.route('/recent-images/<filename>')
def send_recent_image(filename):
    if not ('username' in session):
        return redirect(url_for('login'))

    attached_tag_list = get_tags_attached_to_image(filename)
    all_tag_list = get_tag_list()

    # Get previous and next image
    [previous_image, next_image] = get_previous_and_next_recent_image(filename)

    return render_template('recent_image.html', filename=filename, attached_tag_list=attached_tag_list, all_tag_list=all_tag_list, previous_image=previous_image, next_image=next_image)

@app.route('/images/<filename>')
def send_image(filename):
    if not ('username' in session):
        return redirect(url_for('login'))

    # Get query parameters
    selected_tag_list = request.args.getlist('tag')
    filter_type = request.args.get('filter_type', 'and')

    attached_tag_list = get_tags_attached_to_image(filename)
    all_tag_list = get_tag_list()

    # Get previous and next image
    if len(selected_tag_list) > 0 and filter_type == 'and':
        [previous_image, next_image] = get_previous_and_next_image_and(filename, selected_tag_list)
    elif len(selected_tag_list) > 0 and filter_type == 'or':
        [previous_image, next_image] = get_previous_and_next_image_or(filename, selected_tag_list)
    else:
        [previous_image, next_image] = get_previous_and_next_image(filename)

    return render_template('image.html', filename=filename, attached_tag_list=attached_tag_list, all_tag_list=all_tag_list, previous_image=previous_image, next_image=next_image, selected_tag_list=selected_tag_list, filter_type=filter_type)

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

@app.route('/tags/<tagname>', methods=['POST', 'DELETE'])
def update_tag(tagname):
    if not ('username' in session):
        return redirect(url_for('login'))

    match request.method:
        case 'POST':
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
        case 'DELETE':
            # Delete tag
            delete_tag(tagname)
            flash(f'Tag successfully deleted: {tagname}')

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

@app.route('/zip')
def export_images():
    if not ('username' in session):
        return redirect(url_for('login'))

    # Get filter settings from query parameters or session
    selected_tag_list = request.args.getlist('tag')
    filter_type = request.args.get('filter_type', 'and')

    # Determine the images to include based on filter settings
    if len(selected_tag_list) > 0 and filter_type == 'and':
        image_list = get_image_list_and(selected_tag_list)
    elif len(selected_tag_list) > 0 and filter_type == 'or':
        image_list = get_image_list_or(selected_tag_list)
    else:
        image_list = get_image_list()

    # Create a zip file in memory
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add images to the zip file
        for image in image_list:
            image_path = os.path.join(app.config['IMAGE_FOLDER'], image)
            zf.write(image_path, arcname=image)

    # Prepare the zip file for downloading
    memory_file.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    return send_file(memory_file, download_name=f"exported_images_{timestamp}.zip", as_attachment=True)

@app.route('/slideshow')
def return_slideshow_template():
    if not ('username' in session):
        return redirect(url_for('login'))

    # Get query parameters
    tag_list = request.args.getlist('tag')
    filter_type = request.args.get('filter_type', 'and')
    first_image = request.args.get('first_image')
    random = request.args.get('random')
    interval = request.args.get('interval', 10, type=int) # in seconds

    return render_template('slideshow.html', tag_list=tag_list, filter_type=filter_type, first_image=first_image, random= True if random == 'true' else False, interval=interval)

@app.route('/api/images')
def api_images():
    if not ('username' in session):
        return redirect(url_for('login'))

    # Get query parameters
    selected_tag_list = request.args.getlist('tag')
    filter_type = request.args.get('filter_type', 'and')

    # Get image list
    image_list = service_get_image_list(selected_tag_list, filter_type)

    return jsonify(image_list)

def service_get_image_list(tag_list, filter_type):
    # Get image list displayed on the page
    if len(tag_list) > 0 and filter_type == 'and':
        image_list = get_image_list_and(tag_list)
    elif len(tag_list) > 0 and filter_type == 'or':
        image_list = get_image_list_or(tag_list)
    else:
        # Get all image if no tag is selected or filter type is something but expected
        image_list = get_image_list()

    return image_list

def insert_file_data(filename, hash):
    with get_db() as conn:
        # name will not conflict as timestamp is used as filename so try-except is not necessary
        # Uniqueness of hash is checked before this function is called so try-except is not necessary
        conn.execute('INSERT INTO images (name, hash) VALUES (?, ?)', (filename, hash))

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
    result = get_db().execute('''
                SELECT id
                FROM images
                WHERE hash = ?
            ''', (hash,)).fetchone()

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
    result = get_db().execute('''
            SELECT name
            FROM images
            ORDER BY uploaded_at_utc DESC, name ASC
        ''').fetchall()
    return [row[0] for row in result]

def get_image_list_or(tag_list):
    result = get_db().execute(f'''
            SELECT DISTINCT i.name
            FROM images AS i
            JOIN image_tags AS it
                ON i.id = it.image_id
            JOIN tags AS tg
                ON it.tag_id = tg.id
            WHERE tg.name IN ({','.join(['?'] * len(tag_list))})
            ORDER BY uploaded_at_utc DESC, i.name ASC
        ''', tuple(tag_list)).fetchall()
    return [row[0] for row in result]

def get_image_list_and(tag_list):
    result = get_db().execute(f'''
            SELECT i.name
            FROM images AS i
            JOIN image_tags AS it
                ON i.id = it.image_id
            JOIN tags AS tg
                ON it.tag_id = tg.id
            WHERE tg.name IN ({','.join(['?'] * len(tag_list))})
            GROUP BY i.name
            HAVING COUNT(DISTINCT tg.name) = ?
            ORDER BY uploaded_at_utc DESC, i.name ASC
        ''', tuple(tag_list + [len(tag_list)])).fetchall()
    return [row[0] for row in result]

def get_image_list_recent():
    # select images that are uploaded in last 10 days
    result = get_db().execute('''
            SELECT name
            FROM images
            WHERE uploaded_at_utc > date('now', '-9 days')
            ORDER BY uploaded_at_utc DESC, name ASC
        ''').fetchall()
    return [row[0] for row in result]

def get_previous_and_next_image(filename):
    result = get_db().execute('''
            WITH Ranked AS (
                SELECT
                    name,
                    uploaded_at_utc,
                    LAG(name) OVER (ORDER BY uploaded_at_utc DESC, name ASC) AS preceding_name,
                    LEAD(name) OVER (ORDER BY uploaded_at_utc DESC, name ASC) AS following_name,
                    ROW_NUMBER() OVER (ORDER BY uploaded_at_utc DESC, name ASC) AS row_num
                FROM images
            ),
            Target AS (
                SELECT row_num FROM Ranked WHERE name = ?
            )
            SELECT
                R.name,
                R.uploaded_at_utc
            FROM Ranked R
            JOIN Target T ON R.row_num IN (T.row_num - 1, T.row_num, T.row_num + 1)
            ORDER BY R.uploaded_at_utc DESC, R.name ASC
        ''', (filename,)).fetchall()

    # If the image is the first or last, the result will have only 2 rows
    if len(result) == 2:
        if result[0][0] == filename:
            return (None, result[1][0])
        else:
            return (result[0][0], None)

    # the result have three rows
    assert len(result) == 3
    return (result[0][0], result[2][0])

def get_previous_and_next_image_or(filename, tag_list):
    result = get_db().execute(f'''
            WITH Source AS (
                SELECT i.id, i.name, i.uploaded_at_utc
                FROM images AS i
                JOIN image_tags AS it
                    ON i.id = it.image_id
                JOIN tags AS tg
                    ON it.tag_id = tg.id
                WHERE tg.name IN ({','.join(['?'] * len(tag_list))})
                ORDER BY uploaded_at_utc DESC, i.name ASC
            ),
            Ranked AS (
                SELECT
                    name,
                    uploaded_at_utc,
                    LAG(name) OVER (ORDER BY uploaded_at_utc DESC, name ASC) AS preceding_name,
                    LEAD(name) OVER (ORDER BY uploaded_at_utc DESC, name ASC) AS following_name,
                    ROW_NUMBER() OVER (ORDER BY uploaded_at_utc DESC, name ASC) AS row_num
                FROM Source
            ),
            Target AS (
                SELECT row_num FROM Ranked WHERE name = ?
            )
            SELECT
                R.name,
                R.uploaded_at_utc
            FROM Ranked R
            JOIN Target T ON R.row_num IN (T.row_num - 1, T.row_num, T.row_num + 1)
            ORDER BY R.uploaded_at_utc DESC, R.name ASC
        ''', tuple(tag_list + [filename])).fetchall()

    # If the image is the first or last, the result will have only 2 rows
    if len(result) == 2:
        if result[0][0] == filename:
            return (None, result[1][0])
        else:
            return (result[0][0], None)

    # the result have three rows
    assert len(result) == 3
    return (result[0][0], result[2][0])

def get_previous_and_next_image_and(filename, tag_list):
    result = get_db().execute(f'''
            WITH
            Source AS (
                SELECT i.id, i.name, i.uploaded_at_utc
                FROM images AS i
                JOIN image_tags AS it
                    ON i.id = it.image_id
                JOIN tags AS tg
                    ON it.tag_id = tg.id
                WHERE tg.name IN ({','.join(['?'] * len(tag_list))})
                GROUP BY i.name
                HAVING COUNT(DISTINCT tg.name) = ?
                ORDER BY uploaded_at_utc DESC, i.name ASC
            ),
            Ranked AS (
                SELECT
                    name,
                    uploaded_at_utc,
                    LAG(name) OVER (ORDER BY uploaded_at_utc DESC, name ASC) AS preceding_name,
                    LEAD(name) OVER (ORDER BY uploaded_at_utc DESC, name ASC) AS following_name,
                    ROW_NUMBER() OVER (ORDER BY uploaded_at_utc DESC, name ASC) AS row_num
                FROM Source
            ),
            Target AS (
                SELECT row_num FROM Ranked WHERE name = ?
            )
            SELECT
                R.name,
                R.uploaded_at_utc
            FROM Ranked R
            JOIN Target T ON R.row_num IN (T.row_num - 1, T.row_num, T.row_num + 1)
            ORDER BY R.uploaded_at_utc DESC, R.name ASC
        ''', tuple(tag_list + [len(tag_list), filename])).fetchall()

    # If the image is the first or last, the result will have only 2 rows
    if len(result) == 2:
        if result[0][0] == filename:
            return (None, result[1][0])
        else:
            return (result[0][0], None)

    # the result have three rows
    assert len(result) == 3
    return (result[0][0], result[2][0])

def get_previous_and_next_recent_image(filename):
    result = get_db().execute('''
            WITH Ranked AS (
                SELECT
                    name,
                    uploaded_at_utc,
                    LAG(name) OVER (ORDER BY uploaded_at_utc DESC, name ASC) AS preceding_name,
                    LEAD(name) OVER (ORDER BY uploaded_at_utc DESC, name ASC) AS following_name,
                    ROW_NUMBER() OVER (ORDER BY uploaded_at_utc DESC, name ASC) AS row_num
                FROM images
                WHERE uploaded_at_utc > date('now', '-9 days')
            ),
            Target AS (
                SELECT row_num FROM Ranked WHERE name = ?
            )
            SELECT
                R.name,
                R.uploaded_at_utc
            FROM Ranked R
            JOIN Target T ON R.row_num IN (T.row_num - 1, T.row_num, T.row_num + 1)
            ORDER BY R.uploaded_at_utc DESC, R.name ASC
        ''', (filename,)).fetchall()

    # If the image is the first or last, the result will have only 2 rows
    if len(result) == 2:
        if result[0][0] == filename:
            return (None, result[1][0])
        else:
            return (result[0][0], None)

    # the result have three rows
    assert len(result) == 3
    return (result[0][0], result[2][0])

def get_tags_attached_to_image(filename):
    # Read file info from sqlite3
    query_result = get_db().execute('''
                SELECT t.name
                FROM tags AS t
                JOIN image_tags AS it
                    ON t.id = it.tag_id
                JOIN images AS i
                    ON it.image_id = i.id
                WHERE i.name = ?
            ''', (filename,)).fetchall()
    tag_list = [row[0] for row in query_result]
    return tag_list

def get_tag_list():
    tag_list = [row[0] for row in get_db().execute('SELECT name FROM tags').fetchall()]
    return tag_list

def create_tag(tag):
    with get_db() as conn:
        conn.execute('INSERT INTO tags (name) VALUES (?)', (tag,))

def update_tag_name(current, new):
    with get_db() as conn:
        match conn.execute('UPDATE tags SET name = ? WHERE name = ?', (new, current)).rowcount:
            # Can't update the target tag
            case 0: raise ValueError('No tag found')
            # Normal case
            case 1: pass
            # Multiple tags found
            case _: raise ValueError('Multiple tags found')

def delete_tag(tagname):
    with get_db() as conn:
        conn.execute('DELETE FROM tags WHERE name = ?', (tagname,))

def attach_tag_to_image(tag_list, filename):
    # tag_list is a list of tags to attach to the image
    # and tags in tag_list is not attached to the image yet
    # so no need to add try-except for IntegrityError
    with get_db() as conn:
        conn.executemany('''
                    INSERT INTO image_tags (image_id, tag_id)
                    SELECT
                        (SELECT id FROM images WHERE name = ?),
                        (SELECT id FROM tags WHERE name = ?)
                ''', [(filename, tag) for tag in tag_list])

def detach_tag_from_image(tag_list, filename):
    with get_db() as conn:
        conn.executemany('''
                    DELETE FROM image_tags
                    WHERE image_id = (SELECT id FROM images WHERE name = ?)
                    AND tag_id = (SELECT id FROM tags WHERE name = ?)
                ''', [(filename, tag) for tag in tag_list])

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
