import os
import io
import dataset
import json
import uuid
from PIL import Image, ExifTags

from flask import Flask, render_template, request, send_from_directory, jsonify
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
db.create_db_if_not_exists(os.path.join(app.root_path, 'clearfile.sql'),
                           app.config['DB_FILE'])


class APIError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(self)
        self.message = message or ''
        self.status_code = status_code

    def to_dict(self):
        return {
            'status': 'error',
            'message': self.message,
        }


@app.errorhandler(APIError)
def handle_api_error(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


def ok(message=None):
    return json.dumps({
        'status': 'ok',
        'message':  message
        })


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

    if orientation > 1:
        for method in FLIP_METHOD[orientation]:
            img = img.transpose(method)

    return img


@app.route('/')
def web():
    return render_template('index.html')


@app.route('/search', methods=['GET'])
def search():
    if 'query' not in request.args:
        raise APIError('Client must supply query in order to search.')
    conn = dataset.connect(app.config['DB_URL'])
    with conn:
        search = request.args.get('query', default='')
        notes = db.note_search(conn, search,
                               notebook=request.args.get('notebook', None))
        notebooks = db.get_notebooks(conn)
        return render_template('search_result.html',
                               notes=notes,
                               notebooks=notebooks)


@app.route('/note/<uuid>', methods=['GET'])
def get_note(uuid):
    conn = dataset.connect(app.config['DB_URL'])
    with conn:
        try:
            nt = db.note_for_uuid(conn, uuid)
        except KeyError as e:
            raise APIError(e.args[0])
        return json.dumps(nt, cls=note.NoteEncoder)


@app.route('/uploads/<uuid>', methods=['GET'])
def uploads(uuid):
    uuid = secure_filename(uuid)
    return send_from_directory(app.config['CLEARFILE_DIR'], f'{uuid}.jpg')


@app.route('/upload', methods=['POST'])
def handle_upload():
    if 'image' not in request.files or 'title' not in request.form:
        raise APIError('Client must supply both an image and a title field for note uploads.')
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


@app.route('/delete/tag/<tag_id>', methods=['GET'])
def handle_delete_tag(tag_id):
    try:
        tag_id = int(tag_id)
    except ValueError:
        raise APIError('Tag must be an integer.')

    conn = dataset.connect(app.config['DB_URL'])
    with conn:
        db.delete_tag(conn, tag_id)

    return ok()


@app.route('/delete/note/<uuid>', methods=['GET'])
def handle_delete(uuid):
    conn = dataset.connect(app.config['DB_URL'])
    try:
        with conn:
            db.delete_note(conn, uuid)
        path = os.path.join(app.config['CLEARFILE_DIR'], f'{uuid}.jpg')
        os.unlink(path)
        return ok()
    except FileNotFoundError as f:
        raise APIError('Note no longer exists.')


@app.route('/add/notebook', methods=['GET'])
def add_notebook():
    conn = dataset.connect(app.config['DB_URL'])
    notebook = request.args.get('name')
    if notebook is None:
        raise APIError('Client must supply a valid notebook name.')
    with conn:
        db.add_notebook(conn, notebook)
    return ok()


@app.route('/update/note', methods=['POST'])
def update():
    data = request.get_json()
    if not data:
        raise APIError('Please supply valid json data.')
    elif 'uuid' not in data:
        raise APIError('Client must supply UUID to server.')
    conn = dataset.connect(app.config['DB_URL'])
    with conn:
        db.update_note(conn, data)
    return ok()
