##########################################################################################
# picmaker/control.py
##########################################################################################
"""File I/O helpers — read raw image arrays, determine output file path."""

import pathlib
import warnings
from fnmatch import fnmatch

REPLACE_CHOICES = ['all', 'none', 'warn', 'error']


def get_filepaths(files, directory=None, recursive=False, patterns=[], **kwargs):
    """Get a complete list of all filepaths to process.

    Parameters:
        files (str, pathlib.Path or list[str or pathlib.Path]): File names and
            directories.
        directory (str or pathlib.Path, optional): The output directory uf any. By
            default,
        recursive (bool, optional): True to traverse subdirectories.
        patterns (str or list[str], optional): One or more glob patterns. Files found
            inside directories are only included if they match one of these patterns. By
            default, all files are included
        **kwargs: Other input parameters, ignored here.

    Returns:
        (list[pathlib.Path, pathlib.Path]): A list of tuples (input filepath, output
            directory path).
    """

    def _pattern_match(basename, patterns):
        if basename.startswith('.'):
            return False
        for pattern in patterns:
            if fnmatch(basename, pattern):
                return True
        return False

    def _get_outdir(filepath, subdir, directory):
        if directory is None:
            return subdir
        lpath = len(str(filepath))
        remainder = str(subdir)[lpath+1:]
        return directory / remainder

    directory = directory and pathlib.Path(directory)   # convert to pathlib if not None
    patterns = patterns or ['*']

    info = []
    for filepath in files:
        filepath = pathlib.Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f'No such file or directory: "{filepath}"')

        if filepath.is_file():
            info.append((filepath, directory if directory else filepath.parent))

        elif filepath.is_dir():
            if recursive:
                for (subdir, _, basenames) in filepath.walk(follow_symlinks=True):
                    basenames.sort()
                    for basename in basenames:
                        if _pattern_match(basename, patterns):
                            info.append((subdir / basename,
                                         _get_outdir(filepath, subdir, directory)))
            else:
                basenames = [child.name for child in filepath.iterdir()]
                for basename in basenames:
                    if _pattern_match(basename, patterns):
                        info.append((filepath / basename,
                                     _get_outdir(filepath, filepath, directory)))

        else:
            raise OSError(f'not a file or directory: "{filepath}"')

    return info


def get_outfile(inpath, outdir=None, *, strip=[], suffix='', extension='jpg',
                replace='all', **kwargs):
    """Derive the output filepath for one input path.

    Parameters:
        inpath (str or pathlib.Path): The input file.
        outdir (str or pathlib.Path, optional): Output directory, or ``None`` to use the
            input's directory.
        strip (str or list[str], optional): A string or list of strings to strip from the
            input filepath before appending the suffix.
        suffix (str, operational): Extra string added before the extension.
        extension (str, optional): Output file extension, whihch defines the output
            format, (e.g. ``'jpg'``).
        replace (str, optional): Replacement policy when the output file already exists:
            ``'all'`` (silent overwrite), ``'none'`` (skip silently), ``'warn'`` (warn and
            overwrite), or ``'error'`` (raise OSError).
        **kwargs: Additional input parameters, ignored here.

    Returns:
        The output file path, or an empty string when ``replace='none'`` and the file
            already exists.

    Raises:
        OSError: If ``replace='error'`` and the file already exists.

    Side Effects:
        Creates the output directory tree if it does not exist.
    """

    replace = replace or 'all'
    replace = replace.lower()
    if replace not in REPLACE_CHOICES:
        raise ValueError(f'unrecognized replace option: {replace!r}')

    inpath = pathlib.Path(inpath)
    outdir = inpath.parent if outdir is None else pathlib.Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    stem = inpath.stem
    if strip:
        if isinstance(strip, str):
            strip = [strip]
        for substring in strip:
            stem = stem.replace(substring, '')

    if suffix:
        stem += suffix

    outpath = outdir / (stem + '.' + extension.lstrip('.'))
    if outpath.exists():
        if replace == 'none':
            return ''
        elif replace == 'warn':
            warnings.warn(f'File overwritten: {outpath}', UserWarning, stacklevel=2)
        elif replace == 'error':
            raise OSError(f'File already exists: {outpath}')

    return outpath


__all__ = ['REPLACE_CHOICES', 'get_filepaths', 'get_outfile']

##########################################################################################
