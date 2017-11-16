import os
import io
import dataset
import json
import uuid
from PIL import Image, ExifTags

from flask import Flask, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

from clearfile import db, note

app = Flask(__name__)
app.config.update(
    TEMPLATES_AUTO_RELOAD=True
)


def setup_environments():
    clearfile_dir = os.environ.get('CLEARFILE_DIR')
    db_file = os.path.join(clearfile_dir, 'clearfile.db')
    app.config['CLEARFILE_DIR'] = clearfile_dir
    app.config['DB_FILE'] = db_file
    app.config['DB_URL'] = f'sqlite:///{db_file}'


setup_environments()
db.create_db_if_not_exists(os.path.join(app.root_path, 'clearfile.sql'), app.config['DB_FILE'])


def make_error(message):
    return json.dumps({
        'status': 'error',
        'message': message
    })


def ok(message=None):
    return json.dumps({
        'status': 'ok',
        'message':  message
    })


ORENTATION_EXIF_TAG = 51041

FLIP_METHOD = {
    2: [Image.FLIP_LEFT_RIGHT],
    3: [Image.ROTATE_180],
    4: [Image.FLIP_TOP_BOTTOM],
    5: [Image.FLIP_LEFT_RIGHT, Image.ROTATE_90],
    6: [Image.ROTATE_270],
    7: [Image.FLIP_LEFT_RIGHT, Image.ROTATE_270],
    8: [Image.ROTATE_90]
}


def restore_rotation(img):
    exifdict = img._getexif()
    orientation = 1

    for k, v in exifdict.items():
        if ExifTags.TAGS[k] == 'Orientation':
            orientation = v
            break

    print(orientation)
    if orientation > 1:
        for method in FLIP_METHOD[orientation]:
            img = img.transpose(method)

    return img


@app.route('/')
def web():
    return render_template('index.html')


@app.route('/search', methods=['GET'])
def search():
    conn = dataset.connect(app.config['DB_URL'])
    with conn:
        search = request.args.get('query', default='')
        if search == '':
            notes = db.get_notes(conn)
        else:
            notes = db.note_search(conn, search)
        return json.dumps(notes, cls=note.NoteEncoder)


@app.route('/note/<uuid>')
def get_note(uuid):
    conn = dataset.connect(app.config['DB_URL'])
    with conn:
        note = db.note_for_uuid(conn, uuid)
        return json.dumps(note, cls=note.NoteEncoder)

@app.route('/uploads/<uuid>')
def uploads(uuid):
    uuid = secure_filename(uuid)
    return send_from_directory(app.config['CLEARFILE_DIR'], f'{uuid}.jpg')

@app.route('/upload', methods=['POST'])
def handle_upload():
    image_handle = request.files['image']
    data = image_handle.read()
    image = Image.open(io.BytesIO(data))
    image = restore_rotation(image)
    note_uuid = str(uuid.uuid4())
    filename = f'{note_uuid}.jpg'
    path = os.path.join(app.config['CLEARFILE_DIR'], filename)
    title = request.form['title']
    user_note = note.Note(note_uuid, title)
    note.scan_note(user_note, image=image)
    image.save(path, 'JPEG', quality=80, optimize=True, progressive=True)
    conn = dataset.connect(app.config['DB_URL'])
    with conn:
        db.add_note(conn, user_note)
    return ok()

@app.route('/delete-tag/<tag_id>', methods=['GET'])
def handle_delete_tag(tag_id):
    try:
        tag_id = int(tag_id)
    except ValueError:
        return make_error('Invalid tag id.')

    conn = dataset.connect(app.config['DB_URL'])
    with conn:
        db.delete_tag(conn, tag_id)

    return ok()


@app.route('/delete/<uuid>', methods=['GET'])
def handle_delete(uuid):
    conn = dataset.connect(app.config['DB_URL'])
    try:
        with conn:
            db.delete_note(conn, uuid)
        path = os.path.join(app.config['CLEARFILE_DIR'], f'{uuid}.jpg')
        os.unlink(path)
        return ok()
    except KeyError as e:
        return make_error(e.message)
    except FileNotFoundError as f:
        return make_error('Note no longer exists.')
