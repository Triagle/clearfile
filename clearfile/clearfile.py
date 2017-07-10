import pathlib
import time

import click
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from clearfile import manager


@click.group()
@click.argument('clearfile_dir', type=click.Path(exists=True))
@click.pass_context
def cli(ctx, clearfile_dir):
    ''' Manage and search physical notes stored in a digital clearfile. '''
    ctx.obj = {}
    note_manager = manager.NoteManager(clearfile_dir)
    ctx.obj['note_manager'] = note_manager
    ctx.obj['directory'] = clearfile_dir


VALID_SUFFIXES = {'.png', '.jpe', '.jpeg', '.jpg', '.bmp', '.pnm', '.tiff', '.jfif'}


class NoteEventHandler(FileSystemEventHandler):

    def __init__(self, note_manager):
        super().__init__()
        self.note_manager = note_manager

    def on_created(self, event):
        path = pathlib.PurePath(event.src_path)
        if not event.is_directory and path.suffix in VALID_SUFFIXES:
            with self.note_manager:
                self.note_manager.add_note(path)
            print(f'+ {path.name}')

    def on_moved(self, event):
        path = pathlib.PurePath(event.src_path)
        dest_path = pathlib.PurePath(event.dest_path)
        if not event.is_directory and dest_path.suffix in VALID_SUFFIXES:
            with self.note_manager:
                self.note_manager.rename_note(path, dest_path)

        print(f'{path.name} -> {dest_path.name}')

    def on_deleted(self, event):
        path = pathlib.PurePath(event.src_path)
        print(f'- {path.name}')
        with self.note_manager:
            self.note_manager.remove_note(path)


@cli.command()
@click.pass_obj
def watch(ctx):
    ''' Watch a directory for changes. '''
    note_manager = ctx['note_manager']
    with note_manager:
        note_manager.remove_missing_notes()
    directory = ctx['directory']
    note_watch = NoteEventHandler(note_manager)
    observer = Observer()
    observer.schedule(note_watch, directory, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


@cli.command()
@click.pass_obj
def list(ctx):
    ''' List notes in the clearfile directory. '''
    note_manager = ctx['note_manager']
    with note_manager:
        for note in note_manager.note_tree.walk():
            tags = ', '.join(note.tags)
            print(f'{note.name} ({tags}):')
            print(f'"{note.ocr_text}"')
            print('')


@cli.command()
@click.argument('query')
@click.option('--notebook', default=None, help='Search for notes inside notebook (directory)')
@click.pass_obj
def search(ctx, query, notebook):
    ''' Search notes for a regular expression. '''
    note_manager = ctx['note_manager']

    if notebook is not None:
        notebook = pathlib.Path(notebook)

    with note_manager:
        query_results = note_manager.search_notes(query, notebook=notebook)
        for note in query_results:
            click.echo(note.fullpath)
