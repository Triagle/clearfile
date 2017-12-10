"""Manage notes in a directory."""
import sqlite3
import heapq
from fuzzywuzzy import fuzz

from clearfile import note


def note_for_uuid(db, uuid):
    """For a given uuid, return a note class representing it."""
    dict_note = db['notes'].find_one(uuid=uuid)
    if dict_note is None:
        raise KeyError('Invalid UUID for note.')
    if dict_note['notebook']:
        dict_note['notebook'] = notebook_for_id(db, dict_note['notebook'])
    tags = get_tags_for_note(db, uuid)
    return note.Note(**dict_note, tags=tags)


def get_tags_for_note(db, uuid):
    """Return the tags for a note of a given uuid."""
    return [note.Tag(**tag) for tag in db['tags'].find(uuid=uuid)]


def get_notes(db):
    """Get all notes from the database."""
    notes = []
    for result in db['notes'].all():
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


def closest_matches(query, notes, k=10, lower_bound=None):
    """Return the k closest matches to the search query with a lower bound."""
    heap = []
    for nt in notes:
        score = -rank_note(query, nt)
        if abs(score) < lower_bound:
            continue
        if len(heap) < k or heap[0][0] < score:
            if len(heap) > k:
                heapq.heappop(heap)
            heapq.heappush(heap, (score, nt))

    return [nt for _, nt in heap]


def note_search(conn, search, notebook=None, at=None):
    """Search notes in database based on a query."""
    notes = get_notes(conn)

    if len(search) > 0:
        processed_notes = closest_matches(search, notes, lower_bound=50)
    else:
        processed_notes = notes
    filtered_notes = []

    for n in processed_notes:
        if at is not None and n.location != at:
            continue
        elif notebook and n.notebook is None:
            continue
        elif notebook and n.notebook and n.notebook.name.lower() != notebook.lower():
            continue
        else:
            filtered_notes.append(n)

    return filtered_notes


def add_tags(db, *tags):
    """Add insert new tags into database."""
    db['tags'].insert_many([{
        'uuid': tag.uuid,
        'tag': tag.tag
    } for tag in tags])


def add_note(db, user_note):
    """Add notes to database, also adds tags into database as well."""
    db['notes'].insert(
        dict(
            uuid=user_note.uuid,
            name=user_note.name,
            ocr_text=user_note.ocr_text,
            mime=user_note.mime,
            location=user_note.location))
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
            db['tags'].delete(tag=tag, uuid=nt.uuid)


def update_note(db, data):
    """Update data of note within database."""
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
    """Remove note from database."""
    data = {'uuid': uuid, 'notebook': None}
    db['notes'].update(data, ['uuid'])


def delete_notebook(db, notebook):
    """Delete notebook from database, cascading changes onto all notes."""
    db.query('PRAGMA foreign_keys=ON')
    db['notebooks'].delete(name=notebook)


def add_notebook(db, notebook):
    """Insert new notebook into database."""
    db['notebooks'].insert(dict(name=notebook))


def notebook_for_id(db, id):
    """Return notebook for notebook id."""
    res = db['notebooks'].find_one(id=id)
    return note.Notebook(**res)


def delete_note(db, uuid):
    """Delete note from database, and associated tags."""
    db.query('PRAGMA foreign_keys=ON')
    db['notes'].delete(uuid=uuid)


def get_notebooks(db):
    """Get all notesbooks in the database."""
    return [note.Notebook(**nb) for nb in db['notebooks'].all()]


def delete_tag(db, tag_id):
    """Delete tag from the database."""
    db['tags'].delete(id=tag_id)


def create_db_if_not_exists(schema_file, db_file):
    """Create database if it doesn't exist and excecute intialization schema."""
    conn = sqlite3.connect(db_file)
    with conn:
        with open(schema_file) as f:
            conn.executescript(f.read())
