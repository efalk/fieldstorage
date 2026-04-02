# Overview

This is a drop-in replacement for [cgi.FieldStorage](https://docs.python.org/3.12/library/cgi.html)
which has been removed from Python as of v3.13

It handles GET, HEAD, POST, and POST with multipart/form-data

It has been tested sufficiently for my own applications. I make no guarantees
that it will work in your environment. If you find and fix any bugs, feel free to
submit a pull request.

Unlike the original cgi.FieldStorage class, this variant uses `urllib.parse.parse_qsl()`
and `email.message` to do the heavy lifting. This implementation merely assembles the
results into a form compatible with the original API.


# To use:

    from fieldstorage import FieldStorage

    :

    form = FieldStorage()	# This reads the form data

    source = form.getfirst('source')
    style = form.getfirst('style')

    etc.


# API

## Constructor

    FieldStorage(fp=None, headers=None, outerboundary=b'',
                 environ=os.environ, keep_blank_values=0, strict_parsing=0,
                 limit=None, encoding='utf-8', errors='replace',
                 max_num_fields=None, separator='&')

All arguments are optional, and usually this class can be used successfully
without specifying any.

FieldStorage objects are dictionary-like objects, but that's not the best way
to access them.

Note that since HTML forms allow duplicate item names, each key in the FieldStorage
object may have multiple values. Depending on how you access the item, you may
get a single value or a list of values.

* fp — file-like object to be used for input (POST). Ignored by this implementation
* headers — initial value for headers
* outerbounds — ignored by this implementation
* environ — environment variables
* keep_blank_values — passed to `urllib.parse.parse_qs()`
* strict_parsing — passed to `urllib.parse.parse_qs()`
* limit  — ignored by this implementation
* encoding — passed to `urllib.parse.parse_qs()`
* errors — passed to `urllib.parse.parse_qs()`
* max_num_fields — passed to `urllib.parse.parse_qs()`
* separator — passed to `urllib.parse.parse_qs()`

## Properties

* name: name of the form field
* value: the entire content of the item as bytes (file) or a string (everything else)
* file: a file-like object from which the data can be read \*
* filename: name of file for file inputs, else None
* type: mime-type as a string
* type_options: a dict containing extra informaton from the type
* headers: the HTTP headers for this form part
* disposition: the Content-Disposition header

\* At present, there's little reason to use the `file` property, as the
entire file is kept in memory anyway. Just use the `value` property.
(This was true for the original cgi.FieldStorage as well.)
This is only useful if there's something in your application that was expecting a file.

## Methods

* [key] — dictionary-like indexing. May return a single MiniFieldStorage or
FileFieldStorage object, or a list of such objects if the key had multiple values.
* getvalue(key) — Returns the underlying values rather than MiniFieldStorage objects. Returns a singleton or a list depending on whether there are multiple values for this key.
* getfirst(key) — Returns the first value rather than a list
* getlistt(key) — Returns a list of values, even if there's only one item

# Bugs

The `repr()` function does not return a string that will correctly create a
new FieldStorage.

The original seemed to append extra newlines to some header values. This version
does not do that.
