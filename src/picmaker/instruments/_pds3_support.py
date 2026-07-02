##########################################################################################
# picmaker/instruments/_pds3_support.py
##########################################################################################
"""Shared PDS3 tools."""

import pathlib

import numpy as np
import vax

PDS3_METHODS = ['fast', 'strict', 'loose', 'compound']
DEFAULT_PDS3_METHOD = 'fast'


def read_pds3_image_array(label, obj=None, pointers=None, **kwargs):
    """Return the image array described by a PDS3 label.

    Parameters:
        label (:class:`pdsparser.Pds3Label`): A parsed PDS3 label.
        obj (int, optional): An object index within the file, needed if the label
            describes more than one image object.
        pointers (list[str], optional): Alternative list of names of the IMAGE object
            pointer in the PDS3 label.
        **kwargs: Additional input parameters, ignored here.

    Returns:
        (np.ndarray): a NumPy array containing the pixel values. The array is 3-D if the
        IMAGE object specifies BANDS and 2-D otherwise. The axes are always ordered as
        BANDS (if present), then LINES and SAMPLES. The array preserves the data type and
        byte size of the samples in the file, but has been converted to native byte order.

    Raises:
        KeyError: If ``pointers`` is provided but no named pointer is found in the label.
        IndexError: If ``obj`` is provided but is out of range for the label.
        ValueError: If the label does not describe a readable IMAGE object, lacks a
            pointer, or the data file is shorter than the label describes.
        FileNotFoundError: If the detached data file cannot be found.
    """

    ######################################################################################
    # Identify the IMAGE objects in the label.
    #
    # Each OBJECT in the parsed label appears as a sub-dictionary keyed by the object name
    # (e.g., "IMAGE", or "IMAGE_1", "IMAGE_2", ... if the name is repeated). The
    # sub-dictionary carries an "OBJECT" entry giving the object type. We collect the keys
    # of every sub-dictionary whose type is "IMAGE", preserving the order in which they
    # appear in the label. Any non-IMAGE object (HISTOGRAM, TABLE, etc.) is skipped, so
    # the resulting list can be indexed directly by `obj`.
    ######################################################################################

    if pointers:
        image_key = ''
        for pointer in pointers:
            if pointer in label and isinstance(label[pointer], dict):
                image_key = pointer
                break
        if not image_key:
            raise KeyError(f'IMAGE pointer {pointers[0]} not found')

    else:
        image_keys = [key for key, value in label.items()
                      if key.endswith('IMAGE') and isinstance(value, dict)]
        if not image_keys:
            raise ValueError('label does not describe an IMAGE object')

        # Default to the first IMAGE when no index is given.
        if obj is None:
            image_key = image_keys[0]
        else:
            if obj < -len(image_keys) or obj >= len(image_keys):
                raise IndexError(f'IMAGE index {obj} is out of range')

            image_key = image_keys[obj]

    image = label[image_key]

    ######################################################################################
    # Locate the data file and the byte offset at which the IMAGE begins.
    #
    # Every OBJECT has a matching pointer keyword formed by prefixing its key with "^"
    # (e.g., object "IMAGE_2" uses pointer "^IMAGE_2"). The pointer takes one of two
    # forms:
    #
    #   * A detached pointer, whose value is the name of a separate data file. An
    #     accompanying "<key>_offset" entry (if present) gives the record or byte position
    #     within that file; if absent, the object starts at the beginning.
    #
    #   * An attached pointer, whose value is an integer position within the label's own
    #     file. In this case the data live in the same file from which the label was read.
    #
    # A companion "<key>_unit" entry is "<BYTES>" when the position is measured in bytes,
    # or an empty string when it is measured in records. PDS records and bytes are both
    # numbered starting at 1.
    ######################################################################################

    pointer_key = '^' + image_key
    if pointer_key not in label:
        raise ValueError(f'label has no pointer {pointer_key!r} for the IMAGE object')

    pointer = label[pointer_key]
    unit = label.get(pointer_key + '_unit', '')

    # Determine the directory that holds the data file. Detached file names are
    # interpreted relative to the directory containing the label file; if the label was
    # parsed from a content string rather than a file, fall back to the current working
    # directory.
    label_path = getattr(label, '_filepath', '')
    if label_path:
        base_dir = pathlib.Path(str(label_path)).parent
    else:
        base_dir = pathlib.Path('.')

    if isinstance(pointer, str):
        # Detached pointer: `pointer` is the name of the data file and the position, if
        # any, is carried by the "_offset" companion entry.
        position = label.get(pointer_key + '_offset', 1)
        data_path = _resolve_pds3_filename(base_dir, pointer)
    else:
        # Attached pointer: `pointer` is the position within the label's own file, which
        # therefore also holds the image data.
        position = pointer
        if not label_path:
            raise ValueError('IMAGE uses an attached pointer but the label has no '
                             'associated file')
        data_path = pathlib.Path(str(label_path))

    # Convert the 1-based record or byte position into a 0-based byte offset.
    if unit == '<BYTES>':
        # The position is already a byte number; byte 1 means offset 0.
        byte_offset = max(position - 1, 0)
    else:
        # The position is a record number; convert using RECORD_BYTES. Record 1 (or an
        # unset/zero position) corresponds to an offset of zero.
        if position <= 1:
            byte_offset = 0
        else:
            record_bytes = label['RECORD_BYTES']
            byte_offset = (position - 1) * record_bytes

    ######################################################################################
    # Build the NumPy dtype for a single sample from SAMPLE_TYPE and SAMPLE_BITS.
    #
    # SAMPLE_TYPE encodes both the byte order and the numeric kind. Names that begin with
    # LSB, PC, or VAX are little-endian; all others (MSB, SUN, MAC, IEEE, and the
    # unqualified defaults) are big-endian. The kind is unsigned integer if the name
    # contains "UNSIGNED", floating point for REAL/FLOAT/ DOUBLE, complex for "COMPLEX",
    # and signed integer otherwise.
    #
    # VAX floating-point formats are not IEEE compatible and are not supported here; they
    # are rejected explicitly rather than decoded incorrectly.
    ######################################################################################

    sample_type = str(image['SAMPLE_TYPE']).upper()
    sample_bits = image['SAMPLE_BITS']
    sample_bytes = sample_bits // 8

    if sample_type.startswith(('LSB', 'PC', 'VAX')):
        byteorder = '<'
    else:
        byteorder = '>'

    if 'UNSIGNED' in sample_type or sample_bytes == 1:
        kind = 'u'
    elif 'REAL' in sample_type or 'FLOAT' in sample_type or 'DOUBLE' in sample_type:
        kind = 'f'
    elif 'COMPLEX' in sample_type:
        kind = 'c'
    else:
        kind = 'i'

    # The dtype as stored in the file, carrying the file's byte order.
    vax_float = sample_type.startswith('VAX') and kind in ('f', 'c')
    if vax_float:
        file_dtype = np.dtype(f'<u{sample_bytes}')
    else:
        file_dtype = np.dtype(f'{byteorder}{kind}{sample_bytes}')

    ######################################################################################
    # Work out the on-disk layout from the image dimensions, the optional BANDS /
    # BAND_STORAGE_TYPE, and the per-line prefix/suffix bytes.
    #
    # The file is a sequence of equal-length "line records". Each line record consists of
    # LINE_PREFIX_BYTES, followed by some number of samples, followed by
    # LINE_SUFFIX_BYTES. The prefix and suffix bytes are never part of the image and are
    # skipped. The number of line records and the number of samples per record depend on
    # whether BANDS is present and, if so, on the band storage order:
    #
    #   * No BANDS: LINES records, each LINE_SAMPLES samples.
    #   * BAND_SEQUENTIAL (BSQ): all lines of one band precede the next, giving
    #     BANDS*LINES records of LINE_SAMPLES samples each.
    #   * LINE_INTERLEAVED (BIL): the bands of one line precede the next line, giving
    #     LINES*BANDS records of LINE_SAMPLES samples each.
    #   * SAMPLE_INTERLEAVED (BIP): the bands of one pixel are adjacent, giving LINES
    #     records of LINE_SAMPLES*BANDS samples each.
    ######################################################################################

    lines = image['LINES']
    line_samples = image['LINE_SAMPLES']
    bands = image.get('BANDS')
    storage = image.get('BAND_STORAGE_TYPE', 'BAND_SEQUENTIAL')
    prefix_bytes = image.get('LINE_PREFIX_BYTES', 0)
    suffix_bytes = image.get('LINE_SUFFIX_BYTES', 0)

    if not bands:
        record_count = lines
        samples_per_record = line_samples
    elif storage == 'LINE_INTERLEAVED':
        record_count = lines * bands
        samples_per_record = line_samples
    elif storage == 'SAMPLE_INTERLEAVED':
        record_count = lines
        samples_per_record = line_samples * bands
    else:                                       # BAND_SEQUENTIAL and the default
        record_count = bands * lines
        samples_per_record = line_samples

    ######################################################################################
    # Read the line records and extract just the sample values.
    #
    # We describe one line record as a structured dtype with up to three fields: an opaque
    # prefix block, the sample values, and an opaque suffix block. The opaque blocks use
    # the "void" type so their bytes are read and discarded without interpretation.
    # Reading `record_count` such records and selecting the "samples" field yields a 2-D
    # array of shape (record_count, samples_per_record) holding only the pixels.
    ######################################################################################

    record_fields = []
    if prefix_bytes:
        record_fields.append(('prefix', f'V{prefix_bytes}'))
    record_fields.append(('samples', file_dtype, samples_per_record))
    if suffix_bytes:
        record_fields.append(('suffix', f'V{suffix_bytes}'))
    record_dtype = np.dtype(record_fields)

    # Open the data file, skip the header bytes, and read the line records.
    with open(data_path, 'rb') as f:
        f.seek(byte_offset)
        records = np.fromfile(f, dtype=record_dtype, count=record_count)

    if len(records) != record_count:
        raise ValueError(f'file {data_path} contains fewer image records than the label '
                         'describes')

    samples = records['samples']                # shape (record_count, samples)

    ######################################################################################
    # Reshape the flat sample grid into the final axis order: BANDS (if any), then LINES,
    # then SAMPLES. The reshape/transpose below mirrors the layout rules used above for
    # each storage order.
    ######################################################################################

    if not bands:
        array = samples.reshape(lines, line_samples)
    elif storage == 'LINE_INTERLEAVED':
        # Records are ordered (line, band); move BANDS to the front.
        array = samples.reshape(lines, bands, line_samples).transpose(1, 0, 2)
    elif storage == 'SAMPLE_INTERLEAVED':
        # Each record interleaves bands within each sample; split them out and move BANDS
        # to the front.
        array = samples.reshape(lines, line_samples, bands).transpose(2, 0, 1)
    else:                                       # BAND_SEQUENTIAL
        array = samples.reshape(bands, lines, line_samples)

    ######################################################################################
    # Convert to native byte order. Casting to the same kind and width but with the native
    # byte order swaps bytes as needed and returns a contiguous copy, which also detaches
    # the result from the structured read buffer.
    ######################################################################################

    array = array.astype(file_dtype.newbyteorder('='))

    ######################################################################################
    # Apply SAMPLE_BIT_MASK, if present, to integer data. The mask is a bit pattern that
    # selects the meaningful bits of each sample. Because the AND is purely bit-level, we
    # apply it through an unsigned view of the same width; this sidesteps sign-related
    # casting issues when the mask's high bit is set.
    ######################################################################################

    bit_mask = image.get('SAMPLE_BIT_MASK')
    if bit_mask is not None and kind in ('i', 'u'):
        # Reinterpret the pixels as unsigned integers of the same width, AND in place with
        # the mask, and the change is reflected in `array` because the view shares its
        # memory.
        unsigned_dtype = np.dtype(f'u{sample_bytes}')
        unsigned_view = array.view(unsigned_dtype)
        unsigned_view &= np.array(bit_mask, dtype=unsigned_dtype)

    if vax_float:
        if sample_bytes == 32:
            array = vax.from_vax32(array)
        else:
            array = vax.from_vax64(array)

    return array


def _resolve_pds3_filename(base_dir, name):
    """Return the path to a data file, tolerating case differences.

    The name recorded in a PDS3 label may not match the case used on disk. We first try
    the name exactly as given, then its all-uppercase form, then its all-lowercase form,
    all within `base_dir`.

    Parameters:
        base_dir (pathlib.Path): The directory in which to look for the file.
        name (str): The file name as recorded in the label.

    Returns:
        (pathlib.Path): Path of the first matching file that exists.

    Raises:
        FileNotFoundError: If no matching file is found in ``base_dir``.
    """

    for candidate in (name, name.upper(), name.lower()):
        path = base_dir / candidate
        if path.is_file():
            return path

    raise FileNotFoundError(f'could not find data file {name!r} in {base_dir} '
                            '(tried original, uppercase, and lowercase forms)')


__all__ = ['DEFAULT_PDS3_METHOD', 'PDS3_METHODS', 'read_pds3_image_array']

##########################################################################################
