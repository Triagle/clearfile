import os
import sqlite3
import mimetypes
import json
import uuid

from flask import Flask, render_template, request, send_from_directory

from clearfile import db, note

app = Flask(__name__)
DB_FILE = './static/clearfile/clearfile.db'
SCHEMA_FILE = 'clearfile.sql'
db.create_db_if_not_exists(SCHEMA_FILE, DB_FILE)
app.config.update(
    TEMPLATES_AUTO_RELOAD=True
)
app.config['CLEARFILE_DIR'] = './static/clearfile'


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


@app.route('/')
def web():
    return render_template('index.html')


@app.route('/search', methods=['GET'])
def search():
    conn = sqlite3.connect(DB_FILE)
    with conn:
        search = request.args.get('query', default='')
        if search == '':
            notes = db.get_notes(conn)
        else:
            notes = db.note_search(conn, search)
        return json.dumps(notes, cls=note.NoteEncoder)


@app.route('/note/<uuid>')
def get_note(uuid):
    conn = sqlite3.connect(DB_FILE)
    with conn:
        note = db.note_for_uuid(conn, uuid)
        return json.dumps(note, cls=note.NoteEncoder)

@app.route('/uploads/<uuid>')
def uploads(uuid):
    conn = sqlite3.connect(DB_FILE)
    with conn:
        user_note = db.note_for_uuid(conn, uuid)
        return send_from_directory(app.config['CLEARFILE_DIR'], uuid, mimetype=user_note.mime)

@app.route('/upload', methods=['POST'])
def handle_upload():
    image = request.files['image']
    note_uuid = str(uuid.uuid4())
    mime, _ = mimetypes.guess_type(image.filename)
    path = os.path.join(app.config['CLEARFILE_DIR'], note_uuid)
    path = os.path.abspath(path)
    image.save(path)
    title = request.form['title']
    user_note = note.Note(note_uuid, title, mime, path)
    note.scan_note(path, user_note)
    conn = sqlite3.connect(DB_FILE)
    with conn:
        db.add_note(conn, user_note)
    return ok()

@app.route('/delete-tag/<tag_id>', methods=['GET'])
def handle_delete_tag(tag_id):
    try:
        tag_id = int(tag_id)
    except ValueError:
        return make_error('Invalid tag id.')

    conn = sqlite3.connect(DB_FILE)
    with conn:
        db.delete_tag(conn, tag_id)

    return ok()


@app.route('/delete/<uuid>', methods=['GET'])
def handle_delete(uuid):
    conn = sqlite3.connect(DB_FILE)
    try:
        with conn:
            db.delete_note(conn, uuid)
        path = os.path.join(app.config['CLEARFILE_DIR'], uuid)
        os.unlink(path)
        return ok()
    except KeyError as e:
        return make_error(e.message)
    except FileNotFoundError as f:
        return make_error('Note no longer exists.')
