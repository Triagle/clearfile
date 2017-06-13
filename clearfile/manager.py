import json
import pathlib
import re
try:
    import Image
except ImportError:
    from PIL import Image
import pytesseract


class NoteManager(object):
    def __init__(self, note_dir, database_file='db.json'):
        ''' Initialize NoteManager. '''
        self.note_dir = pathlib.Path(note_dir)
        self.database_file = pathlib.Path(self.note_dir / database_file)
        try:
            with open(self.database_file, 'r') as db_file:
                self.catalog = json.load(db_file)
        except (FileNotFoundError, json.JSONDecodeError):
            self.catalog = {}

    def add_note(self, filename, **tesseract_opts):
        ''' Add a note to the notes catalog. '''
        filepath = self.note_dir / filename
        image = Image.open(filepath)
        self.catalog[filepath.name] = pytesseract.image_to_string(image, **tesseract_opts)
        self.save()

    def remove_missing_notes(self):
        keys_to_remove = []
        for note in self.catalog:
            note_path = self.note_dir / note
            if not note_path.exists():
                keys_to_remove.append(note)
        for key in keys_to_remove:
            del self.catalog[key]

    def rename_note(self, old_name, new_name):
        self.catalog[new_name] = self.catalog[old_name]
        del self.catalog[old_name]

    def search_notes(self, query):
        ''' Search the dictionary of notes for a given search query,
        matching with regex. '''
        results = {}
        for filename, note in self.catalog.items():
            if re.search(query, note, flags=re.IGNORECASE):
                results[filename] = note
        return results

    def save(self):
        with open(self.database_file, 'w') as db_file:
            json.dump(self.catalog, db_file)
