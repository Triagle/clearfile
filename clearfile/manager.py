''' Manage notes in a directory. '''
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


# Buffer size for reading in image files to hash
HASH_BUF_SIZE = 65536


def node_path_for_filepath(path, relativeto):
    ''' Return the node path in the note tree from a given filepath.
    >>> node_path_for_filepath(Path('/home/test/image.png'), Path('/'))
    (('home', 'test'), 'image.png') '''
    path = pathlib.Path(path)
    relpath = path.relative_to(relativeto).parent
    return relpath.parts, path.name


def ellipize(string, limit):
    ''' Ellipize a string, i.e truncate it at limit and append "..."
    >>> ellipize("long string", 5)
    "long ..." '''
    if len(string) > limit:
        return string[:limit] + '...'
    return string


class Note(object):
    ''' Represents a single note (image). Holds information like ocr
    recovered text, the fullpath, keywords, etc. '''

    def __init__(self, name, fullpath, keywords=None, ocr_text=None, old_hash=None):
        ''' Initialize note object. '''
        self.name = name
        self.fullpath = pathlib.Path(fullpath)
        self.keywords = keywords or []
        self.old_hash = old_hash or None
        self.ocr_text = ocr_text or ''

    def scan(self, **tesseract_opts):
        ''' Scan note using tesseract-ocr. '''
        image = Image.open(self.fullpath)
        self.ocr_text = pytesseract.image_to_string(image, **tesseract_opts)

    def path(self, relativeto):
        """ Get the note's path relative to some other path.
        >>> note = Note('myimage.png', '/clearfile/sub/myimage.png')
        >>> note.path('/clearfile')
        ('sub', 'myimage.png') """
        path, _ = node_path_for_filepath(self.fullpath, relativeto)
        return path

    @property
    def hash(self):
        ''' Return the md5 hex digest of the image. '''
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
        """ Returns True if the note's path is still valid. """
        return self.fullpath.exists()

    def __repr__(self):
        ''' Return the representation of the note. '''
        description = ellipize(self.ocr_text, 50)
        class_name = self.__class__.__name__
        return f"{class_name}('{self.name}', '{description}')"


class NoteTree(object):
    ''' Manage a collection of notes and notes within
    directories. Internally this is done by representing the file
    structure of the note directory with a tree. Each node of the tree
    has a notes dictionary mapping filenames to notes, and a children
    dictionary mapping directories to child nodes of the note tree. '''

    def __init__(self):
        ''' Initialize and empty node of the note tree. '''
        self.children = {}
        self.notes = {}

    def _node_for_path(self, path):
        ''' Traverse the note tree following ``path``. Returns None if
        the node at the location described by ``path`` does not exist,
        and the node at the end of ``path`` if it does. '''
        cur_node = self
        for part in path:
            if part not in cur_node.children:
                return None
            else:
                cur_node = cur_node.children[part]

        return cur_node

    def insert(self, path, note):
        ''' Insert ``note`` at the location ``path`` in the note tree. '''
        cur_node = self
        for part in path:
            if part not in cur_node.children:
                cur_node.children[part] = NoteTree()
            cur_node = cur_node.children[part]
        cur_node.notes[note.name] = note

    def remove(self, path, note_name):
        ''' Remove ``note_name`` from the notes dictionary in the node
        at the location described by ``path``. Returns the note that
        was removed, or None if the path given was invalid.  '''
        removal_node = self._node_for_path(path)
        return removal_node.notes.pop(note_name, None)

    def __getitem__(self, path):
        ''' See ``_node_for_path``. '''
        return self._node_for_path(path)

    def __contains__(self, path):
        ''' Returns True if a node exists at the location described by
        ``path``. '''
        return self._node_for_path(path) is not None

    def walk(self):
        ''' A generator that iterates through all notes in the note
        tree. The implementation is a breadth first search, such that
        each level of the tree is fully explored before descending
        into the next level down. '''
        nodes = deque([self])
        while len(nodes) > 0:
            node = nodes.popleft()
            yield from node.notes.values()
            nodes.extend(node.children.values())

    def __repr__(self):
        ''' Display the representation of the note tree. The
        definition is recursive, and will display the entire tree
        including children nodes. '''
        notes = '{' + ', '.join(map(repr, self.notes.values())) + '}'
        children = '{' + ', '.join(map(repr, self.children.values())) + '}'
        name = self.__class__.__name__
        return f'{name}(notes: {notes}, children: {children})'


class TreeEncoder(json.JSONEncoder):
    ''' Encode NoteTree into JSON. '''
    def default(self, obj):
        ''' overridden default to encode NoteTree into JSON. '''
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
    ''' Object hook function to decode JSON into a NoteTree. '''
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


# A set of valid suffixes that are accepted from tesseract.
# TODO: Make this set a complete set of all possible formats recognized by tesseract.
VALID_SUFFIXES = {'.png', '.jpe', '.jpeg', '.jpg'}


class NoteManager(object):
    ''' NoteManager manages the notes directory. NoteManager contains
    functions to sync the state of the notes directory with the
    internal NoteTree representation. '''
    def __init__(self, note_dir, database_file='db.json'):
        ''' Initialize NoteManager. '''
        self.note_dir = pathlib.Path(note_dir)
        self.database_file = pathlib.Path(self.note_dir / database_file)
        self.note_tree = NoteTree()

    def __enter__(self):
        ''' Open note_tree file and deserialize note_tree from json found there. '''
        try:
            with open(self.database_file, 'r') as db_file:
                self.note_tree = json.load(db_file, object_hook=decode_tree)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.note_tree = NoteTree()

    def scan(self):
        ''' Scan notes directory for new notes. '''
        for root, dirs, files in os.walk(self.note_dir):
            tree_path = pathlib.Path(root).relative_to(self.note_dir).parts()
            for file in files:
                note = Note(file, tree_path)
                self.note_tree.insert(tree_path, note)

    def add_note(self, filepath, **tesseract_opts):
        ''' Add a note to the note tree. '''
        note = Note(filepath.name, filepath)
        note.scan()
        self.note_tree.insert(note.path(self.note_dir), note)

    def remove_missing_notes(self):
        ''' Remove notes in the note tree that no longer exist on the
        file system. '''
        notes_to_remove = []
        for note in self.note_tree.walk():
            if not note.exists:
                note_path = note.path(self.note_dir)
                notes_to_remove.append((note_path, note))

        for path, note in notes_to_remove:
            self.note_tree.remove(path, note.name)

    def rename_note(self, old_path, new_path):
        ''' Rename an existing note to a new path. '''
        opath, oname = node_path_for_filepath(old_path, self.note_dir)
        npath, nname = node_path_for_filepath(new_path, self.note_dir)
        old_note = self.note_tree.remove(opath, oname)
        if old_note is not None:
            old_note.name = nname
            self.note_tree.insert(npath, old_note)

    def remove_note(self, note_path):
        ''' Remove an existing note from the note tree. '''
        parts, _ = node_path_for_filepath(note_path, self.note_dir)
        self.note_tree.remove(parts, note_path.name)

    def search_notes(self, query):
        ''' Search the note tree for a given search query,
        matching the OCR'd text with regex. '''
        results = []
        for note in self.note_tree.walk():
            if re.search(query, note.ocr_text, flags=re.IGNORECASE):
                results.append(note)
        return results

    def __exit__(self, exc_type, exc_val, exc_tb):
        ''' Serialize the note tree into JSON, and save it to the
        database file. '''
        with open(self.database_file, 'w') as db_file:
            note_tree_json = TreeEncoder().encode(self.note_tree)
            db_file.write(note_tree_json)
