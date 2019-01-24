#!/usr/bin/env python3
# vim: ts=4 sw=4 ai et

class String(str):
    '''A rich string object for Spawk().
    This object is a string but with extra attributes specifying the
    line number within the input and the fields within the line from
    "string".split().
    '''
    def __new__(cls, s, line_number):
        return super().__new__(cls, s)

    def __init__(self, s, line_number):
        self.line_number = line_number


class Context:
    '''A simple object used as a context which attributes can be set on
    for use between the different functions in a Spawk() processing
    pipeline.'''
    pass
