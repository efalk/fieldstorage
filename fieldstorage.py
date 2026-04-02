"""Meant to be a drop-in replacement for cgi.FieldStorage."""

from email.message import Message
import email.parser
from io import BytesIO, StringIO
import itertools
import os
import sys
import urllib.parse


class MiniFieldStorage(object):
    """Like FieldStorage, but not for files."""

    filename = None
    type = 'text/plain'
    type_options = {}
    disposition = 'form-data'
    disposition_options = None
    headers = {}

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __repr__(self):
        return f"MiniFieldStorage({self.name!r}, {self.value!r})"

    @property
    def file(self):
        return StringIO(self.value)


class FileFieldStorage(MiniFieldStorage):
    """Like MiniFieldStorage, but for files."""

    type = 'application/octet-stream'
    type_options = {}
    disposition = 'application/octet-stream'

    def __init__(self, name, value, filename,
            disposition, disposition_options, headers):
        self.name = name
        self.value = value
        self.filename = filename
        self.disposition = disposition
        self.disposition_options = disposition_options
        self.headers = headers

    def __repr__(self):
        return f"FileFieldStorage({self.name!r}, {self.value!r}, {self.filename!r})"

    @property
    def file(self):
        return BytesIO(self.value)


class FieldStorage(object):
    """Stores a sequence of fields from a form uploaded to
    a cgi script.

    This class is intended as a drop-in replacement for cgi.FieldStorage.
    I don't claim it's perfect, just good enough to let me continue using
    code that was dependent on cgi.FieldStorage.

    It is accessible like a dictionary, whose keys are the names of the
    fields in the form. Values are either Python lists if there were
    multiple fields with the same name, or another FieldStorage object
    or MiniFieldStorage for non-file items.

    A single item contains the following:

        name: field name or None

        filename: filename if specified, else None

        value: Value as a string, or contents of the file as bytes

        file: file-like object from which you can read bytes

        type: content-type if specified, or None

        type_options: dictionary of options from content-type.

        disposition: content-disposition if specified, or None

        headers: email.message.Message containing all headers
    """

    def __init__(self, fp=None, headers=None, outerboundary=b'',
                 environ=os.environ, keep_blank_values=0, strict_parsing=0,
                 limit=None, encoding='utf-8', errors='replace',
                 max_num_fields=None, separator='&'):
        """Constructor. The cgi version did all the heavy lifting, but
        we're just going to let urllib.parse.parse_qs() and email.message
        handle it all."""

        request_method = environ.get('REQUEST_METHOD','GET').upper()
        if headers is None:
            headers = {}

        self.encoding = encoding
        self.errors = errors
        self.bytes_read = 0
        self.limit = limit
        self.headers = headers
        self._items = []

        # Programming note: I originally attempted to implement this with
        # a dict. That started to get complicated, and since the original just
        # used a list, I'm going to go with that.

        # Headers stored internally as a dict. (I'm not sure if HTTP allows
        # multiple headers with the same key, but that won't be in environ
        # anyway.)
        if 'CONTENT_TYPE' in environ:
            headers['content-type'] = environ['CONTENT_TYPE']
        if 'CONTENT_LENGTH' in environ:
            headers['content-length'] = environ['CONTENT_LENGTH']
        for key,value in environ.items():
            if key.startswith('HTTP_'):
                key = key[5:]
                headers[key] = value
        self.headers = headers

        if request_method in ('GET','HEAD'):
            if 'content-type' not in headers:
                headers['content-type'] = "application/x-www-form-urlencoded"

        if request_method in ('POST','PUT'):
            content_len = -1
            if ('content-length') in headers:
                try:
                    content_len = int(headers['content-length'])
                except ValueError:
                    pass
            if content_len < 0:
                raise ValueError("content-length not found")

        if request_method == 'POST' and \
           'multipart/form-data' in environ.get('CONTENT_TYPE','').lower():
            # let mail.message deal with it
            form = {}
            parser = email.parser.BytesFeedParser()
            ct = 'Content-type: ' + environ.get('CONTENT_TYPE','') + '\r\n'
            parser.feed(ct.encode('utf-8'))
            parser.feed(sys.stdin.buffer.read(content_len))
            message = parser.close()
            for part in message.walk():
                if part.is_multipart():
                    continue
                if 'Content-Disposition' in part:
                    disposition, disposition_options = parse_header(part['Content-Disposition'])
                    if 'name' in disposition_options:
                        # OK, it's a real field. Files get packed into
                        # FileFieldStorage objects, everthing else is just
                        # a name:value pair.
                        name = disposition_options['name']
                        if name not in form: form[name] = []
                        if 'filename' not in disposition_options:
                            value = part.get_payload()
                            form[name].append(value)
                        else:
                            value = part.get_payload(decode=True)
                            part_hdrs = dict(part.items())
                            fs = FileFieldStorage(name, value, disposition_options['filename'],
                                    disposition, disposition_options, part_hdrs)
                            form[name].append(fs)

        else:
            # TODO: older servers might pass the query string in argv[1]; look
            # into handling that.
            if request_method == 'POST':
                form = urllib.parse.parse_qs(sys.stdin.read(content_len),
                    keep_blank_values=keep_blank_values,
                    strict_parsing=strict_parsing,
                    encoding=encoding, errors=errors,
                    max_num_fields=max_num_fields, separator=separator)
            else:
                form = urllib.parse.parse_qs(environ.get('QUERY_STRING',''),
                    keep_blank_values=keep_blank_values,
                    strict_parsing=strict_parsing,
                    encoding=encoding, errors=errors,
                    max_num_fields=max_num_fields, separator=separator)

        self._form = form

    def __del__(self):
        # Not clear if any cleanup is required yet
        pass

    def __enter__(self):
        return self
    def __exit__(self):
        # Not clear if any cleanup is required yet
        pass

    def __repr__(self):
        return f"FieldStorage(None, None, {self._form!r})"

    def __getitems(self, key):
        """Internal: return the list of matching MiniFieldStorage items."""
        values = self._form[key]
        rval = []
        for value in values:
            if isinstance(value, FileFieldStorage):
                rval.append(value)
            else:
                rval.append(MiniFieldStorage(key, value))
        return rval

    def __getitem__(self, key):
        rval = self.__getitems(key)
        if not rval:
            raise KeyError(key)
        return rval[0] if len(rval) == 1 else rval

    def keys(self):
        return self._form.keys()

    @property
    def value(self):
        """Return all values, as a list of MiniFieldStorage objects."""
        # What we return depends on what we contain
        if self._form:
            rval = []
            for key in self._form.keys():
                value = self[key]
                try:
                    rval.extend(value)
                except TypeError:
                    rval.append(value)
            return rval
        return None

    def getvalue(self, key, default=None):
        """Return the value(s) for this key, as a singleton or a list"""
        value = self._form[key]
        if not value: return default
        return value[0] if len(value) == 1 else value

    def getfirst(self, key, default=None):
        """Return the first value for this key, as a singleton"""
        value = self._form[key]
        if not value: return default
        return value[0]

    def getlist(self, key, default=None):
        """Return the value(s) for this key, as a list"""
        value = self._form[key]
        if not value: return default
        return value


# UTILITIES, use if you want

def parse_header(line):
    """Parse a content-type header, return (type, optiondict)"""
    # See https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Type
    # The format is the content type, followed by name=value pairs separated by ';'
    line = line.split(';')
    line = [x.strip() for x in line]
    type = line.pop(0)
    optiondict = {}
    for item in line:
        key,value = item.split('=',1)
        if value.startswith('"'): value = value.strip('"')
        optiondict[key] = value
    return (type, optiondict)
