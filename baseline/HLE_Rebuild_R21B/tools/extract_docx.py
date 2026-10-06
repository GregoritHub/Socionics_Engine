#!/usr/bin/env python3
"""Reproduce paragraph locators without rendering or changing the originals.

Pxxxx counts every w:p under w:body, including empty/table-cell paragraphs.
Both Word text and Office Math text are retained in document order.
"""
import argparse
import xml.etree.ElementTree as E
from pathlib import Path
from zipfile import ZipFile


def extract(path):
    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
        'm':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
    with ZipFile(path) as z:tree=E.fromstring(z.read('word/document.xml'))
    rows=[]
    for n,paragraph in enumerate(tree.findall('.//w:body//w:p',ns),1):
        text=''.join(el.text or '' for el in paragraph.iter()
                     if el.tag in ('{'+ns['w']+'}t','{'+ns['m']+'}t'))
        if text.strip():rows.append(f'P{n:04d} {text}')
    return '\n'.join(rows)+'\n'


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('input',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();args.output.write_text(extract(args.input))
