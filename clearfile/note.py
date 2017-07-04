from clearfile import keywords
import json
import pathlib
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
    recovered text, the fullpath, tags, etc. '''

    def __init__(self, name, fullpath, tags=None, ocr_text=None, old_hash=None):
        ''' Initialize note object. '''
        self.name = name
        self.fullpath = pathlib.Path(fullpath)
        if tags:
            self.tags = set(tags)
        else:
            self.tags = set()
        self.old_hash = old_hash or None
        self.ocr_text = ocr_text or ''

    def scan(self, **tesseract_opts):
        ''' Scan note using tesseract-ocr. '''
        image = Image.open(self.fullpath)
        self.ocr_text = pytesseract.image_to_string(image, **tesseract_opts)
        self.tags = keywords.keywords_of('en_NZ', self.ocr_text)

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
                    'tags': list(obj.tags),
                    'hash': obj.old_hash,
                    'ocr_text': obj.ocr_text}
        elif isinstance(obj, pathlib.PurePath):
            return {'__path__': str(obj)}
        return json.JSONEncoder.default(self, obj)


def decode_tree(dct):
    ''' Object hook function to decode JSON into a NoteTree. '''
    if '__node__' in dct:
        node = NoteTree()
        node.children = dct['children'] or {}
        node.notes = dct['notes'] or {}
        return node
    elif '__note__' in dct:
        return Note(dct['name'],
                    dct['fullpath'],
                    tags=dct['tags'],
                    ocr_text=dct['ocr_text'],
                    old_hash=dct['hash'])
    elif '__path__' in dct:
        return pathlib.Path(dct['__path__'])
    return dct
