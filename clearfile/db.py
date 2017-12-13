"""Manage notes in a directory."""
import sqlite3
import heapq
from fuzzywuzzy import fuzz

from clearfile import note


def note_for_uuid(db, uuid):
    """For a given uuid, return a note class representing it."""
    dict_note = db.execute('select * from notes where uuid = ?', (uuid,)).fetchone()
    dict_note = dict(dict_note)
    if dict_note is None:
        raise KeyError('Invalid UUID for note.')
    if dict_note['notebook']:
        dict_note['notebook'] = notebook_for_id(db, dict_note['notebook'])
    tags = get_tags_for_note(db, uuid)
    return note.Note(**dict_note, tags=tags)


def get_tags_for_note(db, uuid):
    """Return the tags for a note of a given uuid."""
    tags = db.execute('select * from tags where uuid = ?', (uuid,))
    return [note.Tag(**tag) for tag in tags.fetchall()]


def get_notes(db):
    """Get all notes from the database."""
    notes = []
    results = db.execute('select * from notes')
    for result in results.fetchall():
        result = dict(result)
        if result.get('notebook', None):
            result['notebook'] = notebook_for_id(db, result['notebook'])
        tags = get_tags_for_note(db, result['uuid'])
        notes.append(note.Note(**result, tags=tags))

    return notes


def rank_note(query, note):
    """Rank a note's similarity to a query (max of match on title and text)."""
    match_ocr = fuzz.WRatio(query, note.ocr_text)
    match_title = fuzz.WRatio(query, note.name)
    return max(match_ocr, match_title)


def note_search(conn, search, notebook=None, at=None):
    """Search notes in database based on a query."""
    notes = get_notes(conn)
    filtered_notes = []

    for n in notes:
        if at and n.location != at:
            continue
        elif notebook and n.notebook is None:
            continue
        elif notebook and n.notebook and n.notebook.name.lower() != notebook.lower():
            continue
        else:
            score = rank_note(search, n)
            if search == '' or score > 50:
                filtered_notes.append((score, n))

    largest = heapq.nlargest(10, filtered_notes, key=lambda r: r[0])
    return [nt for _, nt in largest]


def add_tags(db, *tags):
    """Add insert new tags into database."""
    db.executemany('insert into tags (uuid, tag) values (?, ?)',
                   [(tag.uuid, tag.tag) for tag in tags])


def add_note(db, user_note):
    """Add notes to database, also adds tags into database as well."""
    db.execute('insert into notes (uuid, name, ocr_text, mime, location) values (?, ?, ?, ?, ?)',
               (user_note.uuid, user_note.name, user_note.ocr_text, user_note.mime, user_note.location))
    add_tags(db, *user_note.tags)


def update_tags(db, nt, new_tags):
    """Update tags of note within database, only including changes to tag set."""
    old_tags = {tag.tag for tag in nt.tags}
    new_tags = set(new_tags)

    for tag in new_tags ^ old_tags:
        if tag in new_tags:
            new_tag = note.Tag(None, nt.uuid, tag)
            add_tags(db, new_tag)
        elif tag in old_tags:
            db.execute('delete from tags where uuid = ?, tag = ?', (nt.uuid, tag))


def update_note(db, uuid, data):
    """Update data of note within database."""
    old_note = note_for_uuid(db, uuid)
    if 'tags' in data:
        update_tags(db, old_note, data['tags'])
        data.pop('tags')
    if 'notebook' in data and old_note.notebook and data['notebook'] != old_note.notebook:
        query = 'select * from notes where notebook = ?'
        notes_left = db.execute(query, (old_note.notebook.id,)).fetchall()
        if len(list(notes_left)) == 1:
            db.execute('delete from notebooks where id = ?', (old_note.notebook.id,))

    query = '''update notes
    set
    name = ?,
    mime = ?,
    ocr_text = ?,
    location = ?,
    notebook = ?
    where uuid = ?
    '''
    db.execute(query, (data.get('name', old_note.name),
                       data.get('mime', old_note.mime),
                       data.get('ocr_text', old_note.ocr_text),
                       data.get('location', old_note.location),
                       data.get('notebook', old_note.notebook),
                       uuid))


def remove_note_from_notebook(db, uuid):
    """Remove note from database."""
    update_note(db, uuid, {'notebook': None})


def delete_notebook(db, notebook):
    """Delete notebook from database, cascading changes onto all notes."""
    query = 'delete from notebooks where name=?'
    db.execute(query, (notebook,))


def add_notebook(db, notebook):
    """Insert new notebook into database."""
    query = 'insert into notebooks (name) values (?)'
    db.execute(query, (notebook,))


def notebook_for_id(db, id):
    """Return notebook for notebook id."""
    query = 'select * from notebooks where id = ?'
    res = db.execute(query, (id,)).fetchone()
    return note.Notebook(**res)


def delete_note(db, uuid):
    """Delete note from database, and associated tags."""
    db.execute('delete from notes where uuid = ?', (uuid,))


def get_notebooks(db):
    """Get all notesbooks in the database."""
    notes = db.execute('select * from notebooks').fetchall()
    return [note.Notebook(**nb) for nb in notes]


def delete_tag(db, tag_id):
    """Delete tag from the database."""
    db.execute('delete from tags where id = ?', (tag_id,))


def create_db_if_not_exists(schema_file, db_file):
    """Create database if it doesn't exist and excecute intialization schema."""
    conn = sqlite3.connect(db_file)
    with conn:
        with open(schema_file) as f:
            conn.executescript(f.read())
