"""Main web server of clearfile.

Responsible for handling client interactions and maintaining core databases.
"""
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
    """Initialize file and url environments for app configuration."""
    clearfile_dir = os.environ.get('CLEARFILE_DIR')
    db_file = os.path.join(clearfile_dir, 'clearfile.db')
    app.config['CLEARFILE_DIR'] = clearfile_dir
    app.config['DB_FILE'] = db_file
    app.config['DB_URL'] = f'sqlite:///{db_file}'


setup_environments()
db.create_db_if_not_exists(os.path.join(app.root_path, 'clearfile.sql'),
                           app.config['DB_FILE'])


class APIError(Exception):
    """Generic container for API interaction errors."""

    def __init__(self, message, status_code=400):
        """Initialize error with message and status (defaults to 400)."""
        super().__init__(self)
        self.message = message or ''
        self.status_code = status_code

    def to_dict(self):
        """Return error as dictionary, useful for serialization to JSON."""
        return {
            'status': 'error',
            'message': self.message
        }


@app.errorhandler(APIError)
def handle_api_error(error):
    """Handle a raised APIError by returning a formatted JSON response of the error's details."""
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


def ok(message=None):
    """Return a generic JSON ok response."""
    return json.dumps({
        'status': 'ok',
        'message':  message
    })


# A table mapping EXIF oreintation tags to rotations/reflections.
# EXIF oreintation tags describe the camera's oreintation relative to the captured image.
# See http://jpegclub.org/exif_orientation.html for oreintation details.
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
    """Restore correct rotation of the image by inspecting the EXIF data of the image."""
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
    """Return default index.html view."""
    return render_template('index.html')


@app.route('/search', methods=['GET'])
def search():
    """Respond to a search query with formatted notes.

    Query is matched against note titles and scanned texts, notes are formatted as HTML.
    """
    if 'query' not in request.args:
        raise APIError('Client must supply query in order to search.')
    conn = dataset.connect(app.config['DB_URL'])
    with conn:
        search = request.args.get('query', default='')
        notes = db.note_search(conn, search,
                               notebook=request.args.get('notebook', None))
        notebooks = db.get_notebooks(conn)
        # See search_result.html for details on how notes are converted to HTML note cards.
        return render_template('search_result.html',
                               notes=notes,
                               notebooks=notebooks)


@app.route('/note/<uuid>', methods=['GET'])
def get_note(uuid):
    """Get note details (formatted as JSON) by note UUID."""
    conn = dataset.connect(app.config['DB_URL'])
    with conn:
        try:
            nt = db.note_for_uuid(conn, uuid)
        except KeyError as e:
            raise APIError(e.args[0])
        return json.dumps(nt, cls=note.NoteEncoder)


@app.route('/uploads/<uuid>', methods=['GET'])
def uploads(uuid):
    """Show note image associated with note UUID."""
    uuid = secure_filename(uuid)
    return send_from_directory(app.config['CLEARFILE_DIR'], f'{uuid}.jpg')


@app.route('/upload', methods=['POST'])
def handle_upload():
    """Add new note to database, based on uploaded data.

    Client must supply note title and image, other information is found via processing the image.
    """
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
    """Delete tag from database based on tag id."""
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
    """Delete note from database based on note UUID, also deleting tags attached to that note."""
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
    """Add new notebook to database."""
    conn = dataset.connect(app.config['DB_URL'])
    notebook = request.args.get('name')
    if notebook is None:
        raise APIError('Client must supply a valid notebook name.')
    with conn:
        db.add_notebook(conn, notebook)
    return ok()


@app.route('/update/note', methods=['POST'])
def update():
    """Update note details in database.

    Client must supply UUID of note to change, along with valid JSON data representing
    properties to edit. Tags are updated on a diff-like basis, i.e client supplies a new list
    of tags, and tags are removed/added appropriately.
    """
    data = request.get_json()
    if not data:
        raise APIError('Please supply valid json data.')
    elif 'uuid' not in data:
        raise APIError('Client must supply UUID to server.')
    conn = dataset.connect(app.config['DB_URL'])
    with conn:
        db.update_note(conn, data)
    return ok()
