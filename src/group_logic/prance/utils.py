
# Raise the given exception class from the caught exception, preserving
# stack trace and message as much as possible.
from urllib import parse

# Map file name extensions to parse/serialize functions
__EXT_TO_FORMAT = {
    (".yaml", ".yml"): "YAML",
    (".json", ".js"): "JSON",
}

__MIME_TO_FORMAT = {
    ("application/json", "application/javascript"): "JSON",
    ("application/yaml", "text/yaml"): "YAML",
}


#: Resolve internal references
RESOLVE_INTERNAL = 2**1
#: Resolve references to HTTP external files.
RESOLVE_HTTP = 2**2
#: Resolve references to local files.
RESOLVE_FILES = 2**3

#: Copy the schema changing the reference.
TRANSLATE_EXTERNAL = 0
#: Replace the reference with inlined schema.
TRANSLATE_DEFAULT = 1

#: Default, resole all references.
RESOLVE_ALL = RESOLVE_INTERNAL | RESOLVE_HTTP | RESOLVE_FILES


# Re-define an error for backwards compatibility
FileNotFoundError = FileNotFoundError  # pragma: no cover


# The following constant and function are taken from
# https://stackoverflow.com/questions/9532499/check-whether-a-path-is-valid-in-python-without-creating-a-file-at-the-paths-ta

# Sadly, Python fails to provide the following magic number for us.
_ERROR_INVALID_NAME = 123
"""
Windows-specific error code indicating an invalid pathname.

See Also
----------
https://msdn.microsoft.com/en-us/library/windows/desktop/ms681382%28v=vs.85%29.aspx
    Official listing of all such codes.
"""


# Following Microsoft documentation, set the default read size for detecting
# a file encoding to a multiple of 4k that seems to work well on various OSes
# and volume sizes.
# https://support.microsoft.com/en-us/help/140365/default-cluster-size-for-ntfs-fat-and-exfat
_READ_CHUNK_SIZE = 64 * 1024
"""
Default read size for detecting file encoding.
"""


def raise_from(klass, from_value, extra_message=None):
    try:
        if from_value is None:
            if extra_message is not None:
                raise klass(extra_message)
            raise klass()

        args = list(from_value.args)
        if extra_message is not None:
            if len(args) and isinstance(args[0], str):
                args[0] += " -- " + extra_message
            else:
                args.append(extra_message)
        raise klass(*args) from from_value
    finally:
        klass = None


class ParseError(ValueError):
    pass  # pragma: nocover


def __format_preferences(filename, content_type):  # noqa: N802
    """
    Detect the format based on file name and content type.

    Each parameter may be None, so a heuristic can be used in the end.

    :return: A tuple of format strings, in the optimal order to try.
    :rtype: tuple
    """
    # Select the correct format.
    # 1) If there is neither file name nor content type, use a heuristic.
    # 2) If there is a file name but no content type, use the file extension.
    # 3) If there is no file name, but a content type, use the content type.
    # 4) If both are present, prefer the content type.
    # 5) use a heuristic either way to catch bad content types, file names,
    #    etc. The selection process above is just the most likely match!
    best = None

    if filename and not content_type:
        from os.path import splitext

        _, ext = splitext(filename)

        for extensions in __EXT_TO_FORMAT.keys():
            if ext in extensions:
                best = __EXT_TO_FORMAT[extensions]

    elif content_type:
        # Split off the first part of the content type; for us, that's enough.
        content_type = content_type.split(";")[0]

        for ctypes in __MIME_TO_FORMAT.keys():
            if content_type in ctypes:
                best = __MIME_TO_FORMAT[ctypes]

    # If we have no best format yet, we need to use a heuristic. This is tricky;
    # Swagger is largely YAML-based, but JSON is used for remote references. In
    # the end, JSON is probably more likely to match.
    if not best:
        best = "JSON"

    # Now assemble an ordered list of formats to return, with the best format
    # first.
    formats = list(__EXT_TO_FORMAT.values())
    formats.remove(best)
    formats.insert(0, best)

    return tuple(formats)


# Basic parse functions
def __parse_yaml(spec_str):  # noqa: N802
    from ruamel.yaml import YAML, parser

    try:
        yaml = YAML(typ="safe")
        return yaml.load(str(spec_str))
    except parser.ParserError as err:
        raise ParseError(str(err))


def __parse_json(spec_str):  # noqa: N802
    import json

    try:
        return json.loads(str(spec_str))
    except ValueError as err:
        raise ParseError(str(err))


# Basic serialization functions
def __serialize_yaml(specs):  # noqa: N802
    import io
    from ruamel.yaml import YAML

    yaml = YAML()
    buf = io.BytesIO()
    yaml.dump(specs, buf)
    return buf.getvalue().decode("UTF-8")


def __serialize_json(specs):  # noqa: N802
    # The default encoding is utf-8, no need to specify it. But we need to switch
    # off ensure_ascii, otherwise we do not get a unicode string back.
    import json

    utf = json.dumps(specs, ensure_ascii=False, indent=2)

    return str(utf)


__FORMAT_TO_PARSER = {
    "YAML": __parse_yaml,
    "JSON": __parse_json,
}

__FORMAT_TO_SERIALIZER = {
    "YAML": __serialize_yaml,
    "JSON": __serialize_json,
}


def format_info(format_name):
    """
    Return content type and extension for a supported format.

    Valid formats are `YAML` or `JSON`.

    :param str format_name: The name of the format.
    :return: The preferred content type and file name extension, or
        (None, None) if the format name is not supported.
    :rtype: tuple
    """
    format_name = format_name.upper()

    content_type = None
    for content_types, name in __MIME_TO_FORMAT.items():
        if name == format_name:
            content_type = content_types[0]

    extension = None
    for extensions, name in __EXT_TO_FORMAT.items():
        if name == format_name:
            extension = extensions[0]

    return content_type, extension


def parse_spec_details(spec_str, filename=None, **kwargs):
    """
    Return a parsed dict of the given spec string.

    Also returned are the detected mime type and file name extension.

    The default format is assumed to be JSON, but if you provide a filename,
    its extension is used to determine whether YAML or JSON should be
    parsed.

    :param str spec_str: The specifications as string.
    :param str filename: [optional] Filename to determine the format from.
    :param str content_type: [optional] Content type to determine the format
        from.
    :return: The specifications, mime type, and extension.
    :rtype: tuple
    :raises ParseError: when parsing fails.
    """
    # Fetch optional content type & determine formats
    content_type = kwargs.get("content_type", None)
    formats = __format_preferences(filename, content_type)

    # Try parsing each format in order
    for f in formats:
        parser = __FORMAT_TO_PARSER[f]
        try:
            result = parser(spec_str)
            ctype, ext = format_info(f)
            return result, ctype, ext
        except ParseError:
            pass

    # All failed!
    raise ParseError("Could not detect format of spec string!")


def parse_spec(spec_str, filename=None, **kwargs):
    """
    Return a parsed dict of the given spec string.

    The function exists for legacy reasons and just wraps parse_spec_details,
    returning only the parsed specs.

    :param str spec_str: The specifications as string.
    :param str filename: [optional] Filename to determine the format from.
    :param str content_type: [optional] Content type to determine the format
        from.
    :return: The specifications.
    :rtype: dict
    :raises ParseError: when parsing fails.
    """
    result, ctype, ext = parse_spec_details(spec_str, filename, **kwargs)
    return result


def serialize_spec(specs, filename=None, **kwargs):
    """
    Return a serialized version of the given spec.

    The default format is assumed to be JSON, but if you provide a filename,
    its extension is used to determine whether YAML or JSON should be
    parsed.

    :param dict specs: The specifications as dict.
    :param str filename: [optional] Filename to determine the format from.
    :param str content_type: [optional] Content type to determine the format
        from.
    :return: The serialized specifications.
    :rtype: str
    """
    # Fetch optional content type & determine formats
    content_type = kwargs.get("content_type", None)
    formats = __format_preferences(filename, content_type)

    # Instead of trying to parse various formats, we only serialize to the first
    # one in the list - nothing else makes much sense.
    serializer = __FORMAT_TO_SERIALIZER[formats[0]]
    return serializer(specs)


def is_pathname_valid(pathname):
    """
    Test whether a path name is valid.

    :return: True if the passed pathname is valid on the current OS, False
        otherwise.
    :rtype: bool
    """
    import errno
    import os

    # If this pathname is either not a string or is but is empty, this pathname
    # is invalid.
    try:
        if not isinstance(pathname, str) or not pathname:
            return False

        # Strip this pathname's Windows-specific drive specifier (e.g., `C:\`)
        # if any. Since Windows prohibits path components from containing `:`
        # characters, failing to strip this `:`-suffixed prefix would
        # erroneously invalidate all valid absolute Windows pathnames.
        _, pathname = os.path.splitdrive(pathname)

        # Directory guaranteed to exist. If the current OS is Windows, this is
        # the drive to which Windows was installed (e.g., the "%SYSTEMDRIVE%"
        # environment variable); else, the typical root directory.
        # The %systemdrive% (typically c:) is the partition with
        # the %systemroot% (typically Windows) directory.
        import sys

        root_dirname = (
            os.environ.get("SYSTEMDRIVE", "C:")
            if sys.platform == "win32"
            else os.path.sep
        )
        assert os.path.isdir(root_dirname)  # ...Murphy and her ironclad Law

        # Append a path separator to this directory if needed.
        root_dirname = root_dirname.rstrip(os.path.sep) + os.path.sep

        # Test whether each path component split from this pathname is valid or
        # not, ignoring non-existent and non-readable path components.
        for pathname_part in pathname.split(os.path.sep):
            try:
                os.lstat(root_dirname + pathname_part)
            except OSError as exc:
                # If an OS-specific exception is raised, its error code
                # indicates whether this pathname is valid or not. Unless this
                # is the case, this exception implies an ignorable kernel or
                # filesystem complaint (e.g., path not found or inaccessible).
                #
                # Only the following exceptions indicate invalid pathnames:
                #
                # * Instances of the Windows-specific "WindowsError" class
                #   defining the "winerror" attribute whose value is
                #   "_ERROR_INVALID_NAME". Under Windows, "winerror" is more
                #   fine-grained and hence useful than the generic "errno"
                #   attribute. When a too-long pathname is passed, for example,
                #   "errno" is "ENOENT" (i.e., no such file or directory) rather
                #   than "ENAMETOOLONG" (i.e., file name too long).
                # * Instances of the cross-platform "OSError" class defining the
                #   generic "errno" attribute whose value is either:
                #   * Under most POSIX-compatible OSes, "ENAMETOOLONG".
                #   * Under some edge-case OSes (e.g., SunOS, *BSD), "ERANGE".
                if hasattr(exc, "winerror"):  # pragma: nocover
                    if exc.winerror == _ERROR_INVALID_NAME:
                        return False
                elif exc.errno in {errno.ENAMETOOLONG, errno.ERANGE}:
                    return False
    # If a "TypeError" exception was raised, it almost certainly has the
    # error message "embedded NUL character" indicating an invalid pathname.
    except TypeError:  # pragma: nocover
        return False
    # Null-bytes may also cause this, and they are invalid.
    except ValueError:
        return False
    # If no exception was raised, all path components and hence this
    # pathname itself are valid. (Praise be to the curmudgeonly python.)
    else:
        return True
    # If any other exception was raised, this is an unrelated fatal issue
    # (e.g., a bug). Permit this exception to unwind the call stack.
    #
    # Did we mention this should be shipped with Python already?


def from_posix(fname):
    """
    Convert a path from posix-like, to the platform format.

    :param str fname: The filename in posix-like format.
    :return: The filename in the format of the platform.
    :rtype: str
    """
    import sys

    if sys.platform == "win32":  # pragma: nocover
        if fname[0] == "/":
            fname = fname[1:]
        fname = fname.replace("/", "\\")
    return fname


def to_posix(fname):
    """
    Convert a path to posix-like format.

    :param str fname: The filename to convert to posix format.
    :return: The filename in posix-like format.
    :rtype: str
    """
    import sys

    if sys.platform == "win32":  # pragma: nocover
        import os.path

        if os.path.isabs(fname):
            fname = "/" + fname
        fname = fname.replace("\\", "/")
    return fname


def abspath(filename, relative_to=None):
    """
    Return the absolute path of a file relative to a reference file.

    If no reference file is given, this function works identical to
    `canonical_filename`.

    :param str filename: The filename to make absolute.
    :param str relative_to: [optional] the reference file name.
    :return: The absolute path
    :rtype: str
    """
    # Create filename relative to the reference, if it exists.
    import os.path

    fname = from_posix(filename)
    if relative_to and not os.path.isabs(fname):
        relative_to = from_posix(relative_to)
        if os.path.isdir(relative_to):
            fname = os.path.join(relative_to, fname)
        else:
            fname = os.path.join(os.path.dirname(relative_to), fname)

    # Make the result canonical
    fname = canonical_filename(fname)
    return to_posix(fname)


def canonical_filename(filename):
    """
    Return the canonical version of a file name.

    The canonical version is defined as the absolute path, and all file system
    links dereferenced.

    :param str filename: The filename to make canonical.
    :return: The canonical filename.
    :rtype: str
    """
    import os.path

    path = from_posix(filename)
    while True:
        path = os.path.abspath(path)
        try:
            p = os.path.dirname(path)
            # os.readlink doesn't exist in windows python2.7
            try:
                deref_path = os.readlink(path)
            except AttributeError:  # pragma: no cover
                return path
            path = os.path.join(p, deref_path)
        except OSError:
            return path


def detect_encoding(filename, default_to_utf8=True, **kwargs):
    """
    Detect the named file's character encoding.

    If the first parts of the file appear to be ASCII, this function returns
    'UTF-8', as that's a safe superset of ASCII. This can be switched off by
    changing the `default_to_utf8` parameter.

    :param str filename: The name of the file to detect the encoding of.
    :param bool default_to_utf8: Defaults to True. Set to False to disable
        treating ASCII files as UTF-8.
    :param bool read_all: Keyword argument; if True, reads the entire file
        for encoding detection.
    :return: The file encoding.
    :rtype: str
    """
    # Read some of the file
    import os.path

    filename = from_posix(filename)
    file_len = os.path.getsize(filename)
    read_len = min(_READ_CHUNK_SIZE, file_len)

    # ... unless we're supposed to!
    if kwargs.get("read_all", False):
        read_len = file_len

    # Read the first read_len bytes raw, so we can detect the encoding
    with open(filename, "rb") as raw_handle:
        raw = raw_handle.read(read_len)

    # Detect the encoding the file specifies, if any.
    import codecs

    if raw.startswith(codecs.BOM_UTF8):
        encoding = "utf-8-sig"
    else:
        # Detect encoding using the best detector available
        try:
            # First try ICU. ICU will report ASCII in the first 32 Bytes as
            # ISO-8859-1, which isn't exactly wrong, but maybe optimistic.
            import icu

            encoding = icu.CharsetDetector(raw).detect().getName().lower()
        except ImportError:  # pragma: nocover
            # If that doesn't work, try chardet - it's not got native components,
            # which is a bonus in some environments, but it's not as precise.
            import chardet

            encoding = chardet.detect(raw)["encoding"].lower()

            # Chardet is more brutal in that it reports ASCII if none of the first
            # Bytes contain high bits. To emulate ICU, we just bump up the detected
            # encoding.
            if encoding == "ascii":
                encoding = "iso-8859-1"

        # Both chardet and ICU may detect ISO-8859-x, which may not be possible
        # to decode as UTF-8. So whatever they report, we'll try decoding as
        # UTF-8 before reporting it.
        if default_to_utf8 and encoding in ("ascii", "iso-8859-1", "windows-1252"):
            # Try decoding as utf-8
            try:
                raw.decode("utf-8")
                # If this worked... well there's no guarantee it's utf-8, to be
                # honest.
                encoding = "utf-8"
            except UnicodeDecodeError:
                # Decoding as utf-8 failed, so we can't default to it.
                pass

    return encoding


def read_file(filename, encoding=None):
    """
    Read and decode a file, taking BOMs into account.

    :param str filename: The name of the file to read.
    :param str encoding: The encoding to use. If not given, detect_encoding is
        used to determine the encoding.
    :return: The file contents.
    :rtype: unicode string
    """
    filename = from_posix(filename)
    if not encoding:
        # Detect encoding
        encoding = detect_encoding(filename)

    # Finally, read the file in the detected encoding
    with open(filename, encoding=encoding) as handle:
        return handle.read()


def write_file(filename, contents, encoding=None):
    """
    Write a file with the given encoding.

    The default encoding is 'utf-8'. It's recommended not to change that for
    JSON or YAML output.

    :param str filename: The name of the file to read.
    :param str contents: The file contents to write.
    :param str encoding: The encoding to use. If not given, detect_encoding is
        used to determine the encoding.
    """
    if not encoding:
        encoding = "utf-8"

    fname = from_posix(filename)
    with open(fname, mode="w", encoding=encoding) as handle:
        handle.write(contents)


def item_iterator(value, path=()):
    """
    Return item iterator over the a nested dict- or list-like object.

    Returns each item value as the second item to unpack, and a tuple path to the
    item as the first value - in that, it behaves much like viewitems(). For list
    like values, the path is made up of numeric indices.

    Given a spec such as this::

      spec = {
        'foo': 42,
        'bar': {
          'some': 'dict',
        },
        'baz': [
          { 1: 2 },
          { 3: 4 },
        ]
      }

    Here, (parts of) the yielded values would be:

      ======== =============
      item     path
      ======== =============
      [...]    ('baz',)
      { 1: 2 } ('baz', 0)
      2        ('baz', 0, 1)
      ======== =============

    :param dict/list value: The specifications to iterate over.
    :return: An iterator over all items in the value.
    :rtype: iterator
    """
    # Yield the top-level object, always
    yield path, value

    from collections.abc import Mapping, Sequence

    # For dict and list like objects, we also need to yield each item
    # recursively.
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield from item_iterator(item, path + (key,))
    elif isinstance(value, Sequence) and not isinstance(value, str):
        for idx, item in enumerate(value):
            yield from item_iterator(item, path + (idx,))


def reference_iterator(specs, path=()):
    """
    Iterate through the given specs, returning only references.

    The iterator returns three values:
      - The key, mimicking the behaviour of other iterators, although
        it will always equal '$ref'
      - The value
      - The path to the item. This is a tuple of all the item's ancestors,
        in sequence, so that you can reasonably easily find the containing
        item. It does not include the final '$ref' key.

    :param dict specs: The specifications to iterate over.
    :return: An iterator over all references in the specs.
    :rtype: iterator
    """
    # We need to iterate through the nested specification dict, so let's
    # start with an appropriate iterator. We can immediately optimize it by
    # only returning '$ref' items.
    for item_path, item in item_iterator(specs, path):
        if len(item_path) <= 0:
            continue
        key = item_path[-1]
        if key == "$ref":
            yield key, item, item_path[:-1]


def _json_ref_escape(path):
    """JSON-reference escape object path."""
    path = str(path)  # Could be an int, etc.
    path = path.replace("~", "~0")
    path = path.replace("/", "~1")
    return path


def _str_path(path):
    """Stringify object path."""
    return "/" + "/".join([_json_ref_escape(p) for p in path])


def path_get(obj, path, defaultvalue=None, path_of_obj=()):
    """
    Retrieve the value from obj indicated by path.

    Like dict.get(), except:

      - Any Mapping or Sequence is supported.
      - Path is itself a Sequence; the first part is applied to the passed
        object, the second part to the value returned from this operation, and
        so forth recursively.

    :param mixed obj: The Sequence or Mapping from which to retrieve values.
    :param Sequence path: A Sequence of zero or more key/index elements.
    :param mixed defaultvalue: If the value at the path does not exist and this
      parameter is not None, it is returned. Otherwise an error is raised.
    """
    from collections.abc import Mapping, Sequence

    # For error reporting.
    path_of_obj_str = _str_path(path_of_obj)

    if path is not None and not isinstance(path, Sequence):
        raise TypeError(
            f"Path is a {type(path)}, but must be None or a Collection!")

    if isinstance(obj, Mapping):
        if path is None or len(path) < 1:
            return obj or defaultvalue

        if path[0] not in obj:
            raise KeyError(
                'Object at "{}" does not contain key: {}'.format(
                    path_of_obj_str, path[0]
                )
            )

        return path_get(
            obj[path[0]], path[1:], defaultvalue, path_of_obj=path_of_obj +
            (path[0],)
        )

    elif isinstance(obj, Sequence):
        if path is None or len(path) < 1:
            return obj or defaultvalue

        try:
            idx = int(path[0])
        except ValueError:
            raise KeyError(
                'Sequence at "%s" needs integer indices only, but got: '
                "%s"
                % (
                    path_of_obj_str,
                    path[0],
                )
            )

        if idx < 0 or idx >= len(obj):
            raise IndexError(
                'Index out of bounds for sequence at "%s": %d' % (
                    path_of_obj_str, idx)
            )

        return path_get(
            obj[idx], path[1:], defaultvalue, path_of_obj=path_of_obj +
            (path[0],)
        )

    else:
        # Path must be empty.
        if path is not None and len(path) > 0:
            raise TypeError(f"Cannot get anything from type {type(obj)}!")
        return obj or defaultvalue


def path_set(obj, path, value, **options):
    """
    Set the value in obj indicated by path.

    Setter anologous to path_get() above.

    As setting values is a write operation, this function optionally creates
    intermediate objects to ensure all elements of path can be dereferenced.

    :param mixed obj: The Sequence or Mapping from which to retrieve values.
    :param Sequence path: A Sequence of zero or more key/index elements.
    :param mixed value: The value to set.
    :param bool create: [optional] Flag indicating whether to create
      intermediate values or not. Defaults to False.
    """
    # Retrieve options
    create = options.get("create", False)

    def fill_sequence(seq, index, value_index_type):
        """
        Fill the sequence seq with elements until index can be accessed.

        Fills with None except for the indexed element. That is either a dict or
        a list, depending on the value_index_type. If the latter is an int, a
        list is added. If the latter is None (unknown), None is added. Otherwise
        a dict is added.
        """
        if len(seq) > index:
            return

        while len(seq) < index:
            seq.append(None)

        if value_index_type == int:
            seq.append([])
        elif value_index_type is None:
            seq.append(None)
        else:
            seq.append({})

    def safe_idx(seq, index):
        """
        Safely index a sequence.

        Much like dict.get with default value, except returns None instead of
        raising IndexError.
        """
        try:
            return type(seq[index])
        except IndexError:
            return None

    # print('obj', obj, type(obj))
    # print('path', path)
    # print('value', value)

    from collections.abc import Sequence, MutableSequence, Mapping, MutableMapping

    if path is not None and not isinstance(path, Sequence):
        raise TypeError(
            f"Path is a {type(path)}, but must be None or a Collection!")

    if len(path) < 1:
        raise KeyError("Cannot set with an empty path!")

    if isinstance(obj, Mapping):
        # If we don't have a mutable mapping, we should raise a TypeError
        if not isinstance(obj, MutableMapping):  # pragma: nocover
            raise TypeError(f"Mapping is not mutable: {type(obj)}")

        # If the path has only one element, we just overwrite the element at the
        # given key. Otherwise we recurse.
        if len(path) == 1:
            if not create and path[0] not in obj:
                # dicts would normally silently create, but we have to make it
                # explicit to fulfil our contract.
                raise KeyError(f'Key "{path[0]}" not in Mapping!')
            obj[path[0]] = value
        else:
            if create and path[0] not in obj:
                if type(path[1]) == int:
                    obj[path[0]] = []
                else:
                    obj[path[0]] = {}
            path_set(obj[path[0]], path[1:], value, create=create)

        return obj

    elif isinstance(obj, Sequence):
        idx = path[0]

        # If we don't have a mutable sequence, we should raise a TypeError
        if not isinstance(obj, MutableSequence):
            raise TypeError(f"Sequence is not mutable: {type(obj)}")

        # Ensure integer indices
        try:
            idx = int(idx)
        except ValueError:
            raise KeyError("Sequences need integer indices only.")

        # If we're supposed to create and the index at path[0] doesn't exist,
        # then we need to push some dummy objects.
        if create:
            fill_sequence(obj, idx, safe_idx(path, 1))

        # If the path has only one element, we just overwrite the element at the
        # given index. Otherwise we recurse.
        # print('pl', len(path))
        if len(path) == 1:
            obj[idx] = value
        else:
            path_set(obj[idx], path[1:], value, create=create)

        return obj
    else:
        raise TypeError(f"Cannot set anything on type {type(obj)}!")


def default_reclimit_handler(limit, parsed_url, recursions=()):
    """Raise prance.util.url.ResolutionError."""
    path = []
    for rc in recursions:
        path.append("{}#/{}".format(rc[0], "/".join(rc[1])))
    path = "\n".join(path)

    raise ResolutionError(
        "Recursion reached limit of %d trying to "
        'resolve "%s"!\n%s' % (limit, parsed_url.geturl(), path)
    )


class RefResolver:
    """Resolve JSON pointers/references in a spec by inlining."""

    def __init__(self, specs, url=None, **options):
        """
        Construct a JSON reference resolver.

        The resolved specs are in the `specs` member after a call to
        `resolve_references` has been made.

        If a URL is given, it is used as a base for calculating the absolute
        URL of relative file references.

        :param dict specs: The parsed specs in which to resolve any references.
        :param str url: [optional] The URL to base relative references on.
        :param dict reference_cache: [optional] Reference cache to use. When
            encountering references, nested RefResolvers are created, and this
            parameter is used by the RefResolver hierarchy to create only one
            resolver per unique URL.
            If you wish to use this optimization across distinct RefResolver
            instances, pass a dict here for the RefResolvers you create
            yourself. It's safe to ignore this parameter in other cases.
        :param int recursion_limit: [optional] set the limit on recursive
            references. The default is 1, indicating that an element may be
            referred to exactly once when resolving references. When the limit
            is reached, the recursion_limit_handler is invoked.
        :param callable recursion_limit_handler: [optional] A callable that
            gets invoked when the recursion_limit is reached. Defaults to
            raising ResolutionError. Receives the recursion_limit as the
            first parameter, and the parsed reference URL as the second. As
            the last parameter, it receives a tuple of references that have
            been detected as recursions.
        :param str encoding: [optional] The encoding to use. If not given,
            detect_encoding is used to determine the encoding.
        :param int resolve_types: [optional] Specify which types of references to
            resolve. Defaults to RESOLVE_ALL.
        :param int resolve_method: [optional] Specify whether to translate external
            references in components/schemas or dereference in place. Defaults
            to TRANSLATE_DEFAULT.
        :param bool strict: [optional] Whether to use strict mode or not; in
            lenient mode, malformed keys will be silently rewritten.
        """
        import copy

        self.specs = copy.deepcopy(specs)
        self.url = url

        self.__reclimit = options.get("recursion_limit", 1)
        self.__reclimit_handler = options.get(
            "recursion_limit_handler", default_reclimit_handler
        )
        self.__reference_cache = options.get("reference_cache", {})
        self.__resolve_types = options.get("resolve_types", RESOLVE_ALL)
        self.__resolve_method = options.get(
            "resolve_method", TRANSLATE_DEFAULT)
        self.__encoding = options.get("encoding", None)
        self.__strict = options.get("strict", True)

        if self.url:
            self.parsed_url = absurl(self.url)
            self._url_key = (urlresource(self.parsed_url), self.__strict)

            # If we have a url, we want to add ourselves to the reference cache
            # - that creates a reference loop, but prevents child resolvers from
            # creating a new resolver for this url.
            if self.specs:
                self.__reference_cache[self._url_key] = self.specs
        else:
            self.parsed_url = self._url_key = None

        self.__soft_dereference_objs = {}

    def resolve_references(self):
        """Resolve JSON pointers/references in the spec."""
        self.specs = self._resolve_partial(self.parsed_url, self.specs, ())

        # If there are any objects collected when using TRANSLATE_EXTERNAL, add
        # them to components/schemas
        if self.__soft_dereference_objs:
            if "components" not in self.specs:
                self.specs["components"] = {}
            if "schemas" not in self.specs["components"]:
                self.specs["components"].update({"schemas": {}})

            self.specs["components"]["schemas"].update(
                self.__soft_dereference_objs)

    def _dereferencing_iterator(self, base_url, partial, path, recursions):
        """
        Iterate over a partial spec, dereferencing all references within.

        Yields the resolved path and value of all items that need substituting.

        :param mixed base_url: URL that the partial specs is located at.
        :param dict partial: The partial specs to work on.
        :param tuple path: The parent path of the partial specs.
        :param tuple recursions: A recursion stack for resolving references.
        """
        for _, refstring, item_path in reference_iterator(partial):
            # Split the reference string into parsed URL and object path
            ref_url, obj_path = split_url_reference(base_url, refstring)
            # print("ref_url", ref_url)
            translate = (self.__resolve_method == TRANSLATE_EXTERNAL) and (
                self.parsed_url.path != ref_url.path
            )

            if self._skip_reference(base_url, ref_url):
                continue

            # The reference path is the url resource and object path
            ref_path = (urlresource(ref_url), tuple(obj_path))

            # Count how often the reference path has been recursed into.
            from collections import Counter

            rec_counter = Counter(recursions)
            next_recursions = recursions + (ref_path,)

            if rec_counter[ref_path] >= self.__reclimit:
                # The referenced value may be produced by the handler, or the handler
                # may raise, etc.
                ref_value = self.__reclimit_handler(
                    self.__reclimit, ref_url, next_recursions
                )
            else:
                # The referenced value is to be used, but let's copy it to avoid
                # building recursive structures.

                ref_value = self._dereference(
                    ref_url, obj_path, next_recursions)
            # Full item path
            full_path = path + item_path
            # First yield parent
            # print("PASSED")
            if translate:
                url = self._collect_soft_refs(ref_url, obj_path, ref_value)
                yield full_path, {"$ref": "#/components/schemas/" + url}
            else:
                # print("full_path", full_path)
                # print("ref_value", ref_value)
                yield full_path, ref_value

    def _collect_soft_refs(self, ref_url, item_path, value):
        """
        Return a portion of the dereferenced url for TRANSLATE_EXTERNAL mode.

        format - ref-url_obj-path
        """
        dref_url = ref_url.path.split("/")[-1] + "_" + "_".join(item_path[1:])
        self.__soft_dereference_objs[dref_url] = value
        return dref_url

    def _skip_reference(self, base_url, ref_url):
        """Return whether the URL should not be dereferenced."""
        if ref_url.scheme.startswith("http"):
            return (self.__resolve_types & RESOLVE_HTTP) == 0
        elif ref_url.scheme == "file" or ref_url.scheme == "python":
            # Internal references
            if base_url.path == ref_url.path:
                return (self.__resolve_types & RESOLVE_INTERNAL) == 0
            # Local files
            return (self.__resolve_types & RESOLVE_FILES) == 0
        else:
            from urllib.parse import urlunparse

            raise ValueError(
                "Scheme {!r} is not recognized in reference URL: {}".format(
                    ref_url.scheme, urlunparse(ref_url)
                )
            )

    def _dereference(self, ref_url, obj_path, recursions):
        """
        Dereference the URL and object path.

        Returns the dereferenced object.

        :param mixed ref_url: The URL at which the reference is located.
        :param list obj_path: The object path within the URL resource.
        :param tuple recursions: A recursion stack for resolving references.
        :return: A copy of the dereferenced value, with all internal references
            resolved.
        """
        # In order to start dereferencing anything in the referenced URL, we have
        # to read and parse it, of course.
        contents = fetch_url(
            ref_url, self.__reference_cache, self.__encoding, self.__strict
        )

        # In this inner parser's specification, we can now look for the referenced
        # object.
        value = contents
        if len(obj_path) != 0:
            # from prance.util.path import path_get

            try:
                value = path_get(value, obj_path)
                value.update({"x-refs": obj_path[-1]})
            except (KeyError, IndexError, TypeError) as ex:
                raise ResolutionError(
                    f'Cannot resolve reference "{ref_url.geturl()}": {str(ex)}'
                )

        # Deep copy value; we don't want to create recursive structures
        import copy

        value = copy.deepcopy(value)
        # Now resolve partial specs
        value = self._resolve_partial(ref_url, value, recursions)

        # That's it!
        return value

    def _resolve_partial(self, base_url, partial, recursions):
        """
        Resolve a (partial) spec's references.

        :param mixed base_url: URL that the partial specs is located at.
        :param dict partial: The partial specs to work on.
        :param tuple recursions: A recursion stack for resolving references.
        :return: The partial with all references resolved.
        """
        # Gather changes from the dereferencing iterator - we need to set new
        # values from the outside in, so we have to post-process this a little,
        # sorting paths by path length.
        changes = dict(
            tuple(self._dereferencing_iterator(
                base_url, partial, (), recursions))
        )

        paths = sorted(changes.keys(), key=len)

        # With the paths sorted, set them to the resolved values.
        # from prance.util.path import path_set

        for path in paths:
            value = changes[path]
            if len(path) == 0:
                partial = value
            else:
                path_set(partial, list(path), value, create=True)

        return partial


def _reference_key(ref_url, item_path):
    """
    Return a portion of the dereferenced URL.

    format - ref-url_obj-path
    """
    return ref_url.path.split("/")[-1] + "_" + "_".join(item_path[1:])


def _local_ref(path):
    url = "#/" + "/".join(path)
    return {"$ref": url}


# Underscored to allow some time for the public API to be stabilized.
class _RefTranslator:
    """
    Resolve JSON pointers/references in a spec by translation.

    References to objects in other files are copied to the /components/schemas
    object of the root document, while being translated to point to the the new
    object locations.
    """

    def __init__(self, specs, url):
        """
        Construct a JSON reference translator.

        The translated specs are in the `specs` member after a call to
        `translate_references` has been made.

        If a URL is given, it is used as a base for calculating the absolute
        URL of relative file references.

        :param dict specs: The parsed specs in which to translate any references.
        :param str url: [optional] The URL to base relative references on.
        """
        import copy

        self.specs = copy.deepcopy(specs)

        self.__strict = True
        self.__reference_cache = {}
        self.__collected_references = {}

        if url:
            self.url = absurl(url)
            url_key = (urlresource(self.url), self.__strict)

            # If we have a url, we want to add ourselves to the reference cache
            # - that creates a reference loop, but prevents child resolvers from
            # creating a new resolver for this url.
            self.__reference_cache[url_key] = self.specs
        else:
            self.url = None

    def translate_references(self):
        """
        Iterate over the specification document, performing the translation.

        Traverses over the whole document, adding the referenced object from
        external files to the /components/schemas object in the root document
        and translating the references to the new location.
        """
        self.specs = self._translate_partial(self.url, self.specs)

        # Add collected references to the root document.
        if self.__collected_references:
            if "components" not in self.specs:
                self.specs["components"] = {}
            if "schemas" not in self.specs["components"]:
                self.specs["components"].update({"schemas": {}})

            self.specs["components"]["schemas"].update(
                self.__collected_references)

    def _dereference(self, ref_url, obj_path):
        """
        Dereference the URL and object path.

        Returns the dereferenced object.

        :param mixed ref_url: The URL at which the reference is located.
        :param list obj_path: The object path within the URL resource.
        :param tuple recursions: A recursion stack for resolving references.
        :return: A copy of the dereferenced value, with all internal references
            resolved.
        """
        # In order to start dereferencing anything in the referenced URL, we have
        # to read and parse it, of course.
        contents = fetch_url(
            ref_url, self.__reference_cache, strict=self.__strict)

        # In this inner parser's specification, we can now look for the referenced
        # object.
        value = contents
        if len(obj_path) != 0:
            # from prance.util.path import path_get

            try:
                value = path_get(value, obj_path)
            except (KeyError, IndexError, TypeError) as ex:
                raise ResolutionError(
                    f'Cannot resolve reference "{ref_url.geturl()}": {str(ex)}'
                )

        # Deep copy value; we don't want to create recursive structures
        import copy

        value = copy.deepcopy(value)

        # Now resolve partial specs
        value = self._translate_partial(ref_url, value)

        # That's it!
        return value

    def _translate_partial(self, base_url, partial):
        changes = dict(
            tuple(self._translating_iterator(base_url, partial, ())))

        paths = sorted(changes.keys(), key=len)

        # from prance.util.path import path_set

        for path in paths:
            value = changes[path]
            if len(path) == 0:
                partial = value
            else:
                path_set(partial, list(path), value, create=True)

        return partial

    def _translating_iterator(self, base_url, partial, path):
        from prance.util.iterators import reference_iterator

        for _, ref_string, item_path in reference_iterator(partial):
            ref_url, obj_path = split_url_reference(base_url, ref_string)
            full_path = path + item_path

            if ref_url.path == self.url.path:
                # Reference to the root document.
                ref_path = obj_path
            else:
                # Reference to a non-root document.
                ref_key = _reference_key(ref_url, obj_path)
                if ref_key not in self.__collected_references:
                    self.__collected_references[ref_key] = None
                    ref_value = self._dereference(ref_url, obj_path)
                    self.__collected_references[ref_key] = ref_value
                ref_path = ["components", "schemas", ref_key]

            ref_obj = _local_ref(ref_path)
            yield full_path, ref_obj


class ResolutionError(LookupError):
    pass


def urlresource(url):
    """
    Return the resource part of a parsed URL.

    The resource part is defined as the part without query, parameters or
    fragment. Just the scheme, netloc and path remains.

    :param tuple url: A parsed URL
    :return: The resource part of the URL
    :rtype: str
    """
    res_list = list(url)[0:3] + [None, None, None]
    return parse.ParseResult(*res_list).geturl()


def absurl(url, relative_to=None):
    """
    Turn relative file URLs into absolute file URLs.

    This is necessary, because while JSON pointers do not allow relative file
    URLs, Swagger/OpenAPI explicitly does. We need to make relative paths
    absolute before passing them off to jsonschema for verification.

    Non-file URLs are left untouched. URLs without scheme are assumed to be file
    URLs.

    :param str/tuple url: The input URL.
    :param str/tuple relative_to: [optional] The URL to which the input URL is
        relative.
    :return: The output URL, parsed into components.
    :rtype: tuple
    """
    # Parse input URL, if necessary
    parsed = url
    if not isinstance(parsed, tuple):

        if is_pathname_valid(url):
            url = to_posix(url)
        try:
            parsed = parse.urlparse(url)
        except Exception as ex:
            raise_from(ResolutionError, ex, f"Unable to parse url: {url}")

    # Any non-file scheme we just return immediately.
    if parsed.scheme not in (None, "", "file"):
        return parsed

    # Parse up the reference URL
    reference = relative_to
    if reference and not isinstance(reference, tuple):

        if is_pathname_valid(reference):

            reference = to_posix(reference)
        reference = parse.urlparse(reference)

    # If the input URL has no path, we assume only its fragment matters.
    # That is, we'll have to set the fragment of the reference URL to that
    # of the input URL, and return the result.
    import os.path

    result_list = None
    if not parsed.path:
        if not reference or not reference.path:
            raise ResolutionError(
                "Cannot build an absolute file URL from a fragment"
                " without a reference with path!"
            )
        result_list = list(reference)
        result_list[5] = parsed.fragment
    elif os.path.isabs(from_posix(parsed.path)):
        # We have an absolute path, so we can ignore the reference entirely!
        result_list = list(parsed)
        result_list[0] = "file"  # in case it was empty
    else:
        # If we have a relative path, we require a reference.
        if not reference:
            raise ResolutionError(
                "Cannot build an absolute file URL from a relative"
                " path without a reference!"
            )
        if reference.scheme not in (None, "", "file"):
            raise ResolutionError(
                "Cannot build an absolute file URL with a non-file" " reference!"
            )

        result_list = list(parsed)
        result_list[0] = "file"  # in case it was empty
        result_list[2] = abspath(from_posix(
            parsed.path), from_posix(reference.path))

    # Reassemble the result and return it
    result = parse.ParseResult(*result_list)
    return result


def split_url_reference(base_url, reference):
    """
    Return a normalized, parsed URL and object path.

    The reference string is a JSON reference, i.e. a URL with a fragment that
    contains an object path into the referenced resource.

    The base URL is used as a reference point for relative references.

    :param mixed base_url: A parsed URL.
    :param str reference: A JSON reference string.
    :return: The parsed absolute URL of the reference and the object path.
    """
    # Parse URL
    parsed_url = absurl(reference, base_url)
    # Grab object path
    obj_path = parsed_url.fragment.split("/")
    while len(obj_path) and not obj_path[0]:
        obj_path = obj_path[1:]

    # Normalize the object path by substituting ~1 and ~0 respectively.
    def _normalize(path):
        path = path.replace("~1", "/")
        path = path.replace("~0", "~")
        return path

    obj_path = [_normalize(p) for p in obj_path]

    return parsed_url, obj_path


def fetch_url_text(url, cache={}, encoding=None):
    """
    Fetch the URL.

    If the URL is a file URL, the format used for parsing depends on the file
    extension. Otherwise, YAML is assumed.

    The URL may also use the `python` scheme. In this scheme, the netloc part
    refers to an importable python package, and the path part to a path relative
    to the package path, e.g. `python://some_package/path/to/file.yaml`.

    :param tuple url: The url, parsed as returned by `absurl` above.
    :param Mapping cache: An optional cache. If the URL can be found in the
      cache, return the cache contents.
    :param str encoding: Provide an encoding for local URLs to override
      encoding detection, if desired. Defaults to None.
    :return: The resource text of the URL, and the content type.
    :rtype: tuple
    """
    url_key = "text_" + urlresource(url)
    entry = cache.get(url_key, None)
    if entry is not None:
        return entry

    # Fetch contents according to scheme. We assume requests can handle all the
    # non-file schemes, or throw otherwise.
    content = None
    content_type = None
    if url.scheme in (None, "", "file"):

        try:
            content = read_file(from_posix(url.path), encoding)
        except FileNotFoundError as ex:

            raise_from(ResolutionError, ex, f"File not found: {url.path}")
    elif url.scheme == "python":
        # Resolve package path
        package = url.netloc
        path = url.path
        if path[0] == "/":
            path = path[1:]

        from importlib.resources import files

        path = files(package).joinpath(path)

        content = read_file(from_posix(path), encoding)
    else:
        import requests

        response = requests.get(url.geturl())
        if not response.ok:  # pragma: nocover
            raise ResolutionError(
                'Cannot fetch URL "%s": %d %s'
                % (url.geturl(), response.status_code, response.reason)
            )
        content_type = response.headers.get("content-type", "text/plain")
        content = response.text

    cache[url_key] = (content, content_type)
    return content, content_type


def fetch_url(url, cache={}, encoding=None, strict=True):
    """
    Fetch the URL and parse the contents.

    Same as fetch_url_text(), but also parses the content and only
    returns the parse results.

    :param tuple url: The url, parsed as returned by `absurl` above.
    :param Mapping cache: An optional cache. If the URL can be found in the
      cache, return the cache contents.
    :param str encoding: Provide an encoding for local URLs to override
      encoding detection, if desired. Defaults to None.
    :return: The parsed file.
    :rtype: dict
    """
    # Return from cache, if parsed result is already present.
    url_key = (urlresource(url), strict)
    entry = cache.get(url_key, None)
    if entry is not None:
        return entry.copy()

    # Fetch URL text
    content, content_type = fetch_url_text(url, cache, encoding=encoding)

    # Parse the result

    result = parse_spec(content, url.path, content_type=content_type)

    # Perform some sanitization in lenient mode.
    if not strict:
        result = stringify_keys(result)

    # Cache and return result
    cache[url_key] = result
    return result.copy()


def stringify_keys(data):
    """
    Recursively stringify keys in a dict-like object.

    :param dict-like data: A dict-like object to stringify keys in.
    :return: A new dict-like object of the same type with stringified keys,
        but the same values.
    """
    from collections.abc import Mapping

    assert isinstance(data, Mapping)

    ret = type(data)()
    for key, value in data.items():
        if not isinstance(key, str):
            key = str(key)
        if isinstance(value, Mapping):
            value = stringify_keys(value)
        ret[key] = value
    return ret


def validation_backends():
    """Return a list of validation backends supported by the environment."""
    ret = []

    try:
        import flex  # noqa: F401

        ret.append("flex")  # pragma: nocover
    except (ImportError, SyntaxError):  # pragma: nocover
        pass

    try:
        import openapi_spec_validator  # noqa: F401

        ret.append("openapi-spec-validator")  # pragma: nocover
    except (ImportError, SyntaxError):  # pragma: nocover
        pass

    try:
        import swagger_spec_validator  # noqa: F401

        ret.append("swagger-spec-validator")  # pragma: nocover
    except (ImportError, SyntaxError):  # pragma: nocover
        pass

    return tuple(ret)


def default_validation_backend():
    """Return the default validation backend, or raise an error."""
    backends = validation_backends()
    if len(backends) <= 0:  # pragma: nocover
        raise RuntimeError(
            "No validation backend available! Install one of "
            '"flex", "openapi-spec-validator" or "swagger-spec-validator".'
        )
    return backends[0]
