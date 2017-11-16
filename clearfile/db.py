''' Manage notes in a directory. '''
import sqlite3
from fuzzywuzzy import process

from clearfile import note


def note_for_uuid(db, uuid):
    ''' For a given uuid, return a note class representing it. '''
    dict_note = db['notes'].find(uuid=uuid)
    tags = get_tags_for_note(db, uuid)
    return note.Note(**dict_note, tags=tags)


def get_tags_for_note(db, uuid):
    ''' Return the tags for a note of a given uuid. '''
    return [
        note.Tag(**tag)
        for tag in db['tags'].find(uuid=uuid)
    ]


def get_notes(db):
    notes = []
    for result in db['notes'].all():
        tags = get_tags_for_note(db, result['uuid'])
        notes.append(note.Note(**result, tags=tags))

    return notes


def note_search(conn, search):
    notes = get_notes(conn)
    text_to_note_map = {note.ocr_text: note for note in notes}
    processed_text = process.extractBests(search, list(text_to_note_map),
                                          limit=10, score_cutoff=50)
    return [text_to_note_map[text] for text, _ in processed_text]


def add_note(db, user_note):
    db['notes'].insert(dict(
        uuid=user_note.uuid,
        name=user_note.name,
        ocr_text=user_note.ocr_text
    ))

    db['tags'].insert_many([
        {'uuid': tag.uuid, 'tag': tag.tag}
        for tag in user_note.tags
    ])


def delete_note(db, uuid):
    _ = db.query('PRAGMA foreign_keys=ON')
    db['notes'].delete(uuid=uuid)


def delete_tag(db, tag_id):
    db['tags'].delete(id=tag_id)


def create_db_if_not_exists(schema_file, db_file):
    conn = sqlite3.connect(db_file)
    with conn:
        with open(schema_file) as f:
            conn.executescript(f.read())
