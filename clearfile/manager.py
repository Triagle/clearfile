import json
import pathlib
import re
import os
import hashlib
from collections import deque
try:
    import Image
except ImportError:
    from PIL import Image
import pytesseract


HASH_BUF_SIZE = 65536


def node_path_for_filepath(path, relativeto):
    path = pathlib.Path(path)
    relpath = path.relative_to(relativeto).parent
    return relpath.parts(), path.name


class Note(object):

    def __init__(self, name, fullpath, keywords=None, ocr_text=None):
        self.name = name
        self.fullpath = pathlib.Path(fullpath)
        self.keywords = keywords or []
        self.old_hash = None
        self.ocr_text = ocr_text or ''

    def scan(self, **tesseract_opts):
        image = Image.open(self.fullpath)
        if self.hash != self.old_hash:
            self.ocr_text = pytesseract.image_to_string(image, **tesseract_opts)

    def path(self, relativeto):
        path, name = node_path_for_filepath(self.fullpath, relativeto)
        return path

    @property
    def hash(self):
        md5 = hashlib.md5()
        with open(self.fullpath, 'rb') as infile:
            while True:
                data = infile.read(HASH_BUF_SIZE)
                if not data:
                    break
                md5.update(data)
        self.old_hash = md5.hexdigest()
        return self.old_hash

    @property
    def exists(self):
        return self.fullpath.exists()

    def __repr__(self):
        description = ocr_text or ''
        description.tr
        return f"{self.__class__.__name__}('{self.name}', )"


class NodeExistsError(Exception):
    pass


class NoteTree(object):

    def __init__(self):
        self.children = {}
        self.notes = {}

    def _node_for_path(self, path):
        cur_node = self
        for part in path:
            if part not in cur_node.children[part]:
                return None
            else:
                cur_node = cur_node.children[part]

        return cur_node

    def insert(self, path, note):
        cur_node = self.node_for_path(path)
        for part in path:
            if part not in cur_node.children[path]:
                cur_node.children[part] = NoteTree()
            cur_node = cur_node.children[part]

        old_note = cur_node.notes.get(note.name, None)
        if old_note is None or old_note.old_hash != note.hash:
            cur_node.notes[note.name] = note

    def remove(self, path, note):
        removal_node = self._node_for_path(path)
        return removal_node.pop(note.name, None)

    def __getitem__(self, path):
        return self._node_for_path(path)

    def __contains__(self, path):
        return self._node_for_path(path) is not None

    def __iter__(self):
        return self

    def __next__(self):
        nodes = deque([self])
        while len(nodes) > 0:
            node = nodes.popleft()
            yield from node.notes.values()
            nodes.extend(node.children.values())


VALID_SUFFIXES = {'.png', '.jpe', '.jpeg', '.jpg'}


class NoteManager(object):
    def __init__(self, note_dir, database_file='db.json'):
        ''' Initialize NoteManager. '''
        self.note_dir = pathlib.Path(note_dir)
        self.database_file = pathlib.Path(self.note_dir / database_file)
        self.note_tree = Note()
        try:
            with open(self.database_file, 'r') as db_file:
                self.catalog = json.load(db_file)
        except (FileNotFoundError, json.JSONDecodeError):
            self.catalog = {}

    def scan(self):
        for root, dirs, files in os.walk(self.note_dir):
            tree_path = pathlib.Path(root).relative_to(self.note_dir).parent
            for file in files:
                note = Note(file, tree_path)
                self.note_tree.insert(tree_path, note)

    def add_note(self, filename, **tesseract_opts):
        ''' Add a note to the notes catalog. '''
        fullpath = self.note_dir / filename
        note = Note(filename, fullpath)
        note.scan()
        self.note_tree.insert(fullpath, note)
        self.save()

    def remove_missing_notes(self):
        notes_to_remove = []
        for note in self.note_tree:
            if not note.exists:
                note_path = note.path(self.note_dir)
                notes_to_remove.append((note_path, note))

        for path, note in notes_to_remove:
            self.note_tree.remove(path, note)

    def rename_note(self, old_path, new_path):
        old_path = pathlib.Path(old_path)
        new_path = pathlib.Path(new_path)
        old_note_path = old_path.relative_to(self.note_dir).parent.parts()
        old_note_name = old_path.name
        new_note_path = new_path.relative_to(self.note_dir).parent.parts()
        new_note_name = new_path.name
        old_note = self.note_tree.remove(old_note_path, old_note_name)
        old_note.name = new_note_name
        self.note_tree.insert(new_note_path, old_note)

    def remove_note(self, note_path):
        path, name = node_path_for_filepath(note_path, self.note_dir)
        self.note_tree.remove(path, name)

    def search_notes(self, query):
        ''' Search the dictionary of notes for a given search query,
        matching with regex. '''
        results = {}
        for note in self.note_tree:
            if re.search(query, note.ocr_text, flags=re.IGNORECASE):
                results[note.name] = note
        return results

    def save(self):
        with open(self.database_file, 'w') as db_file:
            json.dump(self.catalog, db_file)
