# -*- coding: utf-8 -*-
import collections, json, urlutils, time, http.client, urllib.parse


class URLValidator (object):

    @staticmethod
    def next_url (queue, retry):
        result = None
        attempts = 0

        if not queue.empty() or len(retry) is 0:
            result = queue.get()
            if result is None:
                retry.appendleft(( None, None ))

        if result is None:
            if len(retry) is not 0:
                result, attempts = retry.pop()

        return result, attempts

    @staticmethod
    def thread_html (queue, result, max_attempts = 5, sleep = 1.0, test_url = False):

        local_result = {}
        conn = http.client.HTTPSConnection('validator.w3.org')

        try:
            retry = collections.deque()

            while True:
                html, attempts = URLValidator.next_url(queue, retry)

                if html is None:
                    break

                url, code, headers = html

                rep, data = urlutils.make_request(conn, 'POST', '/nu/?out=json', body = code, headers = headers)

                try:
                    if rep is not None:
                        local_result[url] = json.loads(data.decode('utf-8'))

                    elif test_url:
                        rep, data = urlutils.make_request(conn, 'GET', '/nu/?' + urllib.parse.urlencode({
                            'out': 'json',
                            'doc': url.encoded
                        }))

                        if rep is not None:
                            local_result[url] = json.loads(data.decode('utf-8'))
                except ValueError:
                    rep = None

                if rep is None and attempts < max_attempts:
                    retry.append(( html, attempts + 1 ))

                time.sleep(sleep)

        except KeyboardInterrupt:
            pass

        finally:
            conn.close()
            result.update(local_result)

    @staticmethod
    def thread_css (queue, result, max_attempts = 5, sleep = 1.0, warning_level = 2, profile = 'none'):

        local_result = {}
        conn = http.client.HTTPSConnection('jigsaw.w3.org')

        try:
            retry = collections.deque()

            while True:

                url, attemps = URLValidator.next_url(queue, retry)

                if url is None:
                    break

                rep, data = urlutils.make_request(conn, 'GET', '/css-validator/validator?' + urllib.parse.urlencode({
                    'uri': url.encoded,
                    'warning': warning_level,
                    'profile': profile,
                    'output': 'json'
                }))

                try:
                    if rep is not None:
                        local_result[url] = json.loads(data.decode('utf-8'))
                except ValueError:
                    rep = None

                if rep is None and attempts < max_attempts:
                    retry.append(( url, attempts + 1 ))

                time.sleep(sleep)

        except KeyboardInterrupt:
            pass

        finally:
            conn.close()
            result.update(local_result)

    @staticmethod
    def thread_js (queue, result, max_attempts = 5, sleep = 0.0, warning_level = 'VERBOSE', test_url = False):

        local_result = {}
        conn = http.client.HTTPSConnection('closure-compiler.appspot.com')

        try:
            retry = collections.deque()
            headers = { 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8' }

            while True:

                js, attempts = URLValidator.next_url(queue, retry)

                if js is None:
                    break

                url, code = js

                rep, data = urlutils.make_request(conn, 'POST', '/compile', body = (urllib.parse.urlencode({
                    'js_code': code,
                    'warning_level': warning_level
                }) + '&output_format=json&output_info=warnings&output_info=errors').encode('utf-8'), headers = headers)

                try:
                    if rep is not None:
                        local_result[url] = json.loads(data.decode('utf-8'))

                    elif test_url:
                        rep, data = urlutils.make_request(conn, 'POST', '/compile', body = (urllib.parse.urlencode({
                            'code_url': url.encoded,
                            'warning_level': warning_level
                        }) + '&output_format=json&output_info=warnings&output_info=errors').encode('utf-8'), headers = headers)

                        if rep is not None:
                            local_result[url] = json.loads(data.decode('utf-8'))
                except ValueError:
                    rep = None

                if rep is None and attempts < max_attempts:
                    retry.append(( js, attempts + 1 ))

                time.sleep(sleep)

        except KeyboardInterrupt:
            pass

        finally:
            conn.close()
            result.update(local_result)
