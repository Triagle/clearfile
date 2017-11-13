''' Manage notes in a directory. '''
import re
import sqlite3
from fuzzywuzzy import process

from clearfile import note


def note_for_uuid(conn, uuid):
    ''' For a given uuid, return a note class representing it. '''
    cursor = conn.cursor()
    cursor.execute('select uuid, name, ocr_text from notes where notes.uuid = ?', (uuid,))
    result = cursor.fetchone()
    if result is None:
        return None
    result = tuple(result)
    tags = get_tags_for_note(cursor, uuid)
    return note.Note(*result, tags)


def get_tags_for_note(cursor, uuid):
    cursor.execute('select tag_id, tag from tags where tags.note_uuid = ?', (uuid,))
    sqlite_rows = cursor.fetchall()
    tags = []
    for row in sqlite_rows:
        tags.append(note.Tag(*row))
    return tags


def get_notes(conn):
    cursor = conn.cursor()
    results = cursor.execute('select uuid, name, ocr_text from notes')
    notes = []
    for result in results.fetchall():
        tags = get_tags_for_note(cursor, result[0])
        notes.append(note.Note(*result, tags=tags))
    return notes


def note_search(conn, search):
    notes = get_notes(conn)
    text_to_note_map = {note.ocr_text: note for note in notes}
    processed_text = process.extractBests(search, list(text_to_note_map), limit=10, score_cutoff=50)
    return [text_to_note_map[text] for text, _ in processed_text]


def add_note(conn, user_note):
    cursor = conn.cursor()
    cursor.execute('insert into notes (uuid, name, ocr_text) values (?, ?, ?)',
                   (user_note.uuid, user_note.name, user_note.ocr_text))

    for tag in user_note.tags:
        cursor.execute('insert into tags (note_uuid, tag) values (?, ?)', (user_note.uuid, tag))


def delete_note(conn, uuid):
    cursor = conn.cursor()
    if note_for_uuid(conn, uuid) is None:
        raise KeyError(f'Invalid uuid: {uuid}')

    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute('delete from notes where uuid = ?', (uuid,))


def delete_tag(conn, tag_id):
    cursor = conn.cursor()
    cursor.execute('delete from tags where tag_id = ?', (tag_id,))



def create_db_if_not_exists(schema_file, db_file):
    conn = sqlite3.connect(db_file)
    with conn:
        with open(schema_file) as f:
            conn.executescript(f.read())
