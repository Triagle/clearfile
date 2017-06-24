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
    return relpath.parts, path.name


def ellipize(string, limit):
    if len(string) > limit:
        return string[:limit] + '...'
    return string


class Note(object):

    def __init__(self, name, fullpath, keywords=None, ocr_text=None, old_hash=None):
        self.name = name
        self.fullpath = pathlib.Path(fullpath)
        self.keywords = keywords or []
        self.old_hash = old_hash or None
        self.ocr_text = ocr_text or ''

    def scan(self, **tesseract_opts):
        image = Image.open(self.fullpath)
        self.ocr_text = pytesseract.image_to_string(image, **tesseract_opts)

    def path(self, relativeto):
        path, _ = node_path_for_filepath(self.fullpath, relativeto)
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
        description = ellipize(self.ocr_text, 50)
        class_name = self.__class__.__name__
        return f"{class_name}('{self.name}', '{description}')"


class NodeExistsError(Exception):
    pass


class NoteTree(object):

    def __init__(self):
        self.children = {}
        self.notes = {}

    def _node_for_path(self, path):
        cur_node = self
        for part in path:
            if part not in cur_node.children:
                return None
            else:
                cur_node = cur_node.children[part]

        return cur_node

    def insert(self, path, note):
        cur_node = self
        for part in path:
            if part not in cur_node.children:
                cur_node.children[part] = NoteTree(parent=cur_node)
            cur_node = cur_node.children[part]
        cur_node.notes[note.name] = note

    def remove(self, path, note):
        removal_node = self._node_for_path(path)
        return removal_node.notes.pop(note, None)

    def __getitem__(self, path):
        return self._node_for_path(path)

    def __contains__(self, path):
        return self._node_for_path(path) is not None

    def walk(self):
        nodes = deque([self])
        while len(nodes) > 0:
            node = nodes.popleft()
            yield from node.notes.values()
            nodes.extend(node.children.values())

    def __repr__(self):
        notes = '{' + ', '.join(map(repr, self.notes.values())) + '}'
        children = '{' + ', '.join(map(repr, self.children.values())) + '}'
        name = self.__class__.__name__
        return f'{name}(notes: {notes}, children: {children})'


class TreeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, NoteTree):
            return {'__node__': True, 'children': obj.children, 'notes': obj.notes}
        elif isinstance(obj, Note):
            return {'__note__': True,
                    'name': obj.name,
                    'fullpath': obj.fullpath,
                    'keywords': obj.keywords,
                    'hash': obj.old_hash,
                    'ocr_text': obj.ocr_text}
        elif isinstance(obj, pathlib.PurePath):
            return {'__path__': str(obj)}
        return json.JSONEncoder.default(self, obj)


def decode_tree(dct):
    if '__node__' in dct:
        node = NoteTree()
        node.children = dct['children']
        node.notes = dct['notes']
        return node
    elif '__note__' in dct:
        return Note(dct['name'],
                    dct['fullpath'],
                    keywords=dct['keywords'],
                    ocr_text=dct['ocr_text'],
                    old_hash=dct['hash'])
    elif '__path__' in dct:
        return pathlib.Path(dct['__path__'])
    return dct


VALID_SUFFIXES = {'.png', '.jpe', '.jpeg', '.jpg'}


class NoteManager(object):
    def __init__(self, note_dir, database_file='db.json'):
        ''' Initialize NoteManager. '''
        self.note_dir = pathlib.Path(note_dir)
        self.database_file = pathlib.Path(self.note_dir / database_file)
        try:
            with open(self.database_file, 'r') as db_file:
                self.note_tree = json.load(db_file, object_hook=decode_tree)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.note_tree = NoteTree()

    def scan(self):
        for root, dirs, files in os.walk(self.note_dir):
            tree_path = pathlib.Path(root).relative_to(self.note_dir).parts()
            for file in files:
                note = Note(file, tree_path)
                self.note_tree.insert(tree_path, note)

    def add_note(self, filepath, **tesseract_opts):
        ''' Add a note to the notes catalog. '''
        note = Note(filepath.name, filepath)
        note.scan()
        self.note_tree.insert(note.path(self.note_dir), note)
        self.save()

    def remove_missing_notes(self):
        notes_to_remove = []
        for note in self.note_tree.walk():
            if not note.exists:
                note_path = note.path(self.note_dir)
                notes_to_remove.append((note_path, note))

        for path, note in notes_to_remove:
            self.note_tree.remove(path, note.name)

    def rename_note(self, old_path, new_path):
        opath, oname = node_path_for_filepath(old_path, self.note_dir)
        npath, nname = node_path_for_filepath(new_path, self.note_dir)
        old_note = self.note_tree.remove(opath, oname)
        if old_note is not None:
            old_note.name = nname
            self.note_tree.insert(npath, old_note)

    def remove_note(self, note_path):
        parts, _ = node_path_for_filepath(note_path, self.note_dir)
        self.note_tree.remove(parts, note_path.name)

    def search_notes(self, query):
        ''' Search the dictionary of notes for a given search query,
        matching with regex. '''
        results = {}
        for note in self.note_tree.walk():
            if re.search(query, note.ocr_text, flags=re.IGNORECASE):
                results[note.name] = note
        return results

    def save(self):
        with open(self.database_file, 'w') as db_file:
            note_tree_json = TreeEncoder().encode(self.note_tree)
            db_file.write(note_tree_json)
