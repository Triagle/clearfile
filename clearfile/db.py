''' Manage notes in a directory. '''
import sqlite3
from fuzzywuzzy import process

from clearfile import note


def note_for_uuid(db, uuid):
    ''' For a given uuid, return a note class representing it. '''
    dict_note = db['notes'].find_one(uuid=uuid)
    if dict_note is None:
        raise KeyError('Invalid UUID for note.')
    if dict_note['notebook']:
        dict_note['notebook'] = notebook_for_id(db, dict_note['notebook'])
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
        if result.get('notebook', None):
            result['notebook'] = notebook_for_id(db, result['notebook'])
        tags = get_tags_for_note(db, result['uuid'])
        notes.append(note.Note(**result, tags=tags))

    return notes


def note_search(conn, search, notebook=None):
    notes = get_notes(conn)

    if len(search) > 0:
        processed_notes = [text for text, _ in
                           process.extractBests(search, notes,
                                                processor=str,
                                                limit=10, score_cutoff=50)]
    else:
        processed_notes = notes
    filtered_notes = []

    for n in processed_notes:
        if notebook is None:
            filtered_notes.append(n)
        elif n.notebook is None:
            # User specified a notebook but this note has one, continue
            continue
        elif n.notebook.name.lower() == notebook.lower():
            # User specified a notebook and it matches the note we're looking at
            filtered_notes.append(n)

    return filtered_notes


def add_tags(db, *tags):
    db['tags'].insert_many([
        {'uuid': tag.uuid, 'tag': tag.tag}
        for tag in tags
    ])


def add_note(db, user_note):
    db['notes'].insert(dict(
        uuid=user_note.uuid,
        name=user_note.name,
        ocr_text=user_note.ocr_text
    ))
    add_tags(db, *user_note.tags)


def update_tags(db, nt, new_tags):
    old_tags = {tag.tag for tag in nt.tags}
    new_tags = set(new_tags)

    for tag in new_tags ^ old_tags:
        if tag in new_tags:
            new_tag = note.Tag(None, nt.uuid, tag)
            add_tags(db, new_tag)
        elif tag in old_tags:
            db['tags'].delete(tag=tag, uuid=nt.uuid)


def update_note(db, data):
    old_note = note_for_uuid(db, data['uuid'])
    if 'tags' in data:
        update_tags(db, old_note, data['tags'])
        data.pop('tags')
    if 'notebook' in data and old_note.notebook and data['notebook'] != old_note.notebook:
        notes_left = db['notes'].find(notebook=old_note.notebook.id)
        if len(list(notes_left)) == 1:
            db['notebooks'].delete(id=old_note.notebook.id)
    db['notes'].update(data, ['uuid'])



def remove_note_from_notebook(db, uuid):
    data = {'uuid': uuid, 'notebook': None}
    db['notes'].update(data, ['uuid'])


def delete_notebook(db, notebook):
    _ = db.query('PRAGMA foreign_keys=ON')
    db['notebooks'].delete(name=notebook)


def add_notebook(db, notebook):
    db['notebooks'].insert(dict(name=notebook))


def notebook_for_id(db, id):
    res = db['notebooks'].find_one(id=id)
    return note.Notebook(**res)


def delete_note(db, uuid):
    _ = db.query('PRAGMA foreign_keys=ON')
    db['notes'].delete(uuid=uuid)


def get_notebooks(db):
    return [
        note.Notebook(**nb)
        for nb in db['notebooks'].all()
    ]


def delete_tag(db, tag_id):
    db['tags'].delete(id=tag_id)


def create_db_if_not_exists(schema_file, db_file):
    conn = sqlite3.connect(db_file)
    with conn:
        with open(schema_file) as f:
            conn.executescript(f.read())
