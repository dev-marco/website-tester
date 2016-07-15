#!/bin/env python3
# -*- coding: utf-8 -*-
import sys, html.parser, http.client, urllib.parse, xarray

if __name__ == '__main__':
    pass
    # url_data = urllib.parse.urlparse(sys.argv[1], allow_fragments = False)
    #
    # if url_data.netloc == '':
    #     url_data = urllib.parse.urlparse('http://' + sys.argv[1], allow_fragments = False)
    #
    # if url_data.scheme == 'http' or url_data.scheme == 'https':
    #     use_ssl = url_data.scheme == 'https'
    #     start_path = '/' if url_data.path == '' else url_data.path
    #
    #     conn = http.client.HTTPSConnection(url_data.netloc) if use_ssl else http.client.HTTPConnection(url_data.netloc)
    #     conn.request('HEAD', start_path)
    #     rep = conn.getresponse()
    #
    #     if rep.status == 200:
    #         print(rep.reason)
    #     else:
    #         print(rep.status)
    # else:
    #     print('Invalid scheme.')
