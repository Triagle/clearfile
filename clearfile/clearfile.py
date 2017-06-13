import time
import click
import pathlib
from clearfile import manager
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

@click.group()
@click.argument('clearfile_dir', type=click.Path(exists=True))
@click.pass_context
def cli(ctx, clearfile_dir):
    ctx.obj = {}
    note_manager = manager.NoteManager(clearfile_dir)
    ctx.obj['note_manager'] = note_manager
    note_manager.remove_missing_notes()
    ctx.obj['directory'] = clearfile_dir


VALID_SUFFIXES = {'.png', '.jpe', '.jpeg', '.jpg'}


class NoteEventHandler(FileSystemEventHandler):

    def __init__(self, note_manager):
        super().__init__()
        self.note_manager = note_manager

    def on_created(self, event):
        path = pathlib.PurePath(event.src_path)
        if not event.is_directory and path.suffix in VALID_SUFFIXES:
            self.note_manager.add_note(path.name)
            print(f'Added note: {path.name}')

    def on_moved(self, event):
        path = pathlib.PurePath(event.src_path)
        dest_path = pathlib.PurePath(event.dest_path)
        if path.name in self.note_manager.catalog:
            self.note_manager.rename_note(path.name, dest_path.name)
            print(f'{path.name} -> {dest_path.name}')
        elif not event.is_directory and path.suffix in VALID_SUFFIXES:
            self.note_manager.add_note(path.name)

    def on_delete(self, event):
        self.note_manager.remove_missing_notes()
        self.note_manager.save()

@cli.command()
@click.pass_obj
def watch(ctx):
    note_manager = ctx['note_manager']
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
    note_manager.save()


@cli.command()
@click.argument('query')
@click.pass_obj
def search(ctx, query):
    note_manager = ctx['note_manager']
    query_results = note_manager.search_notes(query)
    for filename in query_results:
        click.echo(filename)
