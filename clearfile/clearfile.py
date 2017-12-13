"""Main web server of clearfile.

Responsible for handling client interactions and maintaining core databases.
"""
import os
import io
import sqlite3
import requests
import json
import multiprocessing
import uuid
import mimetypes
from PIL import Image

from flask import Flask, render_template, request, send_from_directory, jsonify, g
from werkzeug.utils import secure_filename

from clearfile import db, note, thumbnail, ocr

app = Flask(__name__)
app.config.update(TEMPLATES_AUTO_RELOAD=True)


def setup_environments():
    """Initialize file and url environments for app configuration."""
    clearfile_dir = os.environ.get('CLEARFILE_DIR')
    db_file = os.path.join(clearfile_dir, 'clearfile.db')
    thumb_dir = os.path.join(clearfile_dir, 'thumb')
    os.makedirs(thumb_dir, exist_ok=True)
    app.config['CLEARFILE_DIR'] = clearfile_dir
    app.config['DB_FILE'] = db_file


setup_environments()
db.create_db_if_not_exists(
    os.path.join(app.root_path, 'clearfile.sql'), app.config['DB_FILE'])


class APIError(Exception):
    """Generic container for API interaction errors."""

    def __init__(self, message, status_code=400):
        """Initialize error with message and status (defaults to 400)."""
        super().__init__(self)
        self.message = message or ''
        self.status_code = status_code

    def to_dict(self):
        """Return error as dictionary, useful for serialization to JSON."""
        return {'status': 'error', 'message': self.message}


@app.errorhandler(APIError)
def handle_api_error(error):
    """Handle a raised APIError by returning a formatted JSON response of the error's details."""
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


def ok(message=None):
    """Return a generic JSON ok response."""
    return json.dumps({'status': 'ok', 'message': message})


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
    search = request.args.get('query', default='')
    notes = db.note_search(
        g.db, search, notebook=request.args.get('notebook', None),
        at=request.args.get('at', None))
    notebooks = db.get_notebooks(g.db)
    # See search_result.html for details on how notes are converted to HTML note cards.
    return render_template(
        'search_result.html', notes=notes, notebooks=notebooks)


@app.route('/note/<uuid>', methods=['GET'])
def get_note(uuid):
    """Get note details (formatted as JSON) by note UUID."""
    try:
        nt = db.note_for_uuid(g.db, uuid)
    except KeyError as e:
        raise APIError(e.args[0])
    return json.dumps(nt, cls=note.NoteEncoder)


@app.route('/uploads/<uuid>', methods=['GET'])
def uploads(uuid):
    """Show note image associated with note UUID."""
    uuid = secure_filename(uuid)

    note = db.note_for_uuid(g.db, uuid)

    mime = note.mime
    extension = mimetypes.guess_extension(mime)
    fp = uuid + extension
    directory = app.config['CLEARFILE_DIR']
    if 'thumb' in request.args and note.has_thumbnail:
        directory = os.path.join(directory, 'thumb')
        fp = uuid + '.jpe'
    return send_from_directory(directory, fp)


LOCATION_SPECIFITY = {'locality', 'premise', 'sublocality'}


def update_location(uuid, gps_data):
    lat, lon = gps_data
    query = f'http://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lon}'
    location = None

    with requests.get(query) as r:
        json = r.json()
        if json['status'] != 'OK':
            return
        result = json['results'][0]
        for component in result['address_components']:
            if set(component['types']) & LOCATION_SPECIFITY:
                location = component['long_name']
                break

    with sqlite3.connect(app.config['DB_FILE']) as conn:
        conn.row_factory = sqlite3.Row
        db.update_note(conn, uuid, {'location': location})

    return location

@app.route('/upload', methods=['POST'])
def handle_upload():
    """Add new note to database, based on uploaded data.

    Client must supply note title and image, other information is found via processing the image.
    """
    g.autoclose = False
    if 'image' not in request.files or 'title' not in request.form:
        raise APIError(
            'Client must supply both an image and a title field for note uploads.'
        )
    title = request.form['title']
    image_handle = request.files['image']
    data = io.BytesIO(image_handle.read())
    mime = image_handle.content_type
    note_uuid = str(uuid.uuid4())
    extension = mimetypes.guess_extension(mime)
    fp = note_uuid + extension
    path = os.path.join(app.config['CLEARFILE_DIR'], fp)
    fetch_location = False
    image = None
    gps_data = None

    if mime.startswith('image/'):
        image = Image.open(data)
        gps_data = ocr.get_gps_position(image)
        image = ocr.restore_rotation(image)
        fetch_location = True
        image.save(path, 'JPEG', quality=80, optimize=True, progressive=True)
    else:
        with open(path, 'wb') as out:
            out.write(data.read())

    user_note = note.Note(note_uuid, title, mime)

    note.scan_note(user_note, path)
    if not user_note.mime.startswith('image/'):
        # generate thumbnail for note.
        thumb_path = os.path.join(app.config['CLEARFILE_DIR'], 'thumb',
                                  f'{user_note.uuid}.jpe')
        thumbnail.create_thumbnail(path, user_note.mime, thumb_path)

    db.add_note(g.db, user_note)
    g.db.commit()
    g.db.close()

    if fetch_location:
        p = multiprocessing.Process(target=update_location, args=(user_note.uuid,gps_data))
        p.start()

    return ok()


@app.route('/delete/tag/<tag_id>', methods=['GET'])
def handle_delete_tag(tag_id):
    """Delete tag from database based on tag id."""
    try:
        tag_id = int(tag_id)
    except ValueError:
        raise APIError('Tag must be an integer.')

    db.delete_tag(g.db, tag_id)

    return ok()


@app.route('/delete/note/<uuid>', methods=['GET'])
def delete_note(uuid):
    """Delete note from database based on note UUID, also deleting tags attached to that note."""
    try:
        note = db.note_for_uuid(g.db, uuid)
        db.delete_note(g.db, uuid)
        extension = mimetypes.guess_extension(note.mime)
        path = os.path.join(app.config['CLEARFILE_DIR'], uuid + extension)
        os.unlink(path)
        return ok()
    except FileNotFoundError as f:
        raise APIError('Note no longer exists.')


@app.route('/add/notebook', methods=['GET'])
def add_notebook():
    """Add new notebook to database."""
    notebook = request.args.get('name')
    if notebook is None:
        raise APIError('Client must supply a valid notebook name.')

    db.add_notebook(g.db, notebook)
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

    uuid = data.pop('uuid')
    db.update_note(g.db, uuid, data)
    return ok()


@app.before_request
def init_db():
    conn = sqlite3.connect(app.config['DB_FILE'])
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    g.db = conn
    g.autoclose = True


@app.after_request
def close_db(response):
    if g.autoclose:
        g.db.commit()
        g.db.close()
    return response
