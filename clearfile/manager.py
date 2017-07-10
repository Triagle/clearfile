''' Manage notes in a directory. '''
import json
import os
import pathlib
import re

from clearfile import note


class NoteManager(object):
    ''' NoteManager manages the notes directory. NoteManager contains
    functions to sync the state of the notes directory with the
    internal NoteTree representation. '''
    def __init__(self, note_dir, database_file='db.json'):
        ''' Initialize NoteManager. '''
        self.note_dir = pathlib.Path(note_dir)
        self.database_file = pathlib.Path(self.note_dir / database_file)
        self.note_tree = note.NoteTree()

    def __enter__(self):
        ''' Open note_tree file and deserialize note_tree from json found there. '''
        try:
            with open(self.database_file, 'r') as db_file:
                self.note_tree = json.load(db_file, object_hook=note.decode_tree)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.note_tree = note.NoteTree()

    def scan(self):
        ''' Scan notes directory for new notes. '''
        for root, dirs, files in os.walk(self.note_dir):
            tree_path = pathlib.Path(root).relative_to(self.note_dir).parts()
            for file in files:
                insert_note = note.Note(file, tree_path)
                self.note_tree.insert(tree_path, insert_note)

    def add_note(self, filepath, **tesseract_opts):
        ''' Add a note to the note tree. '''
        insert_note = note.Note(filepath.name, filepath)
        insert_note.scan()
        self.note_tree.insert(insert_note.path(self.note_dir), insert_note)

    def tag(self, note_path, tags):
        note_path, note_name = note.node_path_for_filepath(note_path, self.note_dir)
        selected_node = self.note_tree[note_path]
        selected_note = selected_node.notes[note_name]
        selected_note.tags.update(tags)

    def remove_missing_notes(self):
        ''' Remove notes in the note tree that no longer exist on the
        file system. '''
        notes_to_remove = []
        for found_note in self.note_tree.walk():
            if not found_note.exists:
                note_path = found_note.path(self.note_dir)
                notes_to_remove.append((note_path, found_note))

        for path, removing_note in notes_to_remove:
            self.note_tree.remove(path, removing_note.name)

    def rename_note(self, old_path, new_path):
        ''' Rename an existing note to a new path. '''
        opath, oname = note.node_path_for_filepath(old_path, self.note_dir)
        npath, nname = note.node_path_for_filepath(new_path, self.note_dir)
        old_note = self.note_tree.remove(opath, oname)
        if old_note is not None:
            old_note.name = nname
            self.note_tree.insert(npath, old_note)
        else:
            # Treat as normal insertion
            self.add_note(new_path)

    def remove_note(self, note_path):
        ''' Remove an existing note from the note tree. '''
        parts, _ = note.node_path_for_filepath(note_path, self.note_dir)
        self.note_tree.remove(parts, note_path.name)

    def search_notes(self, query, notebook=None):
        ''' Search the note tree for a given search query,
        matching the OCR'd text with regex. '''
        results = []

        if notebook is not None:
            node = self.note_tree[notebook]
        else:
            node = self.note_tree


        for candidate_note in node.walk():
            if re.search(query, candidate_note.ocr_text, flags=re.IGNORECASE):
                results.append(candidate_note)
        return results

    def __exit__(self, exc_type, exc_val, exc_tb):
        ''' Serialize the note tree into JSON, and save it to the
        database file. '''
        with open(self.database_file, 'w') as db_file:
            note_tree_json = note.TreeEncoder().encode(self.note_tree)
            db_file.write(note_tree_json)
