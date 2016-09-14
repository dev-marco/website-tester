#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, zlib, gzip, re, socket, uuid, time, signal, argparse, textwrap
import http.client
import urllib.parse, urllib.request, urllib.error, urllib.robotparser

import multiprocessing as mp, multiprocessing.managers

import urlutils, urlhttp, urldeque, urlfinder, urlcookie, urlvalidator

from color import Color


if __name__ == '__main__':

    PROG_VERSION = '0.01a'
    PROG_URL = 'https://github.com/dev-marco/website-tester'

    DEFAULT_UA = 'Webtestbot/{0} (+{1})'.format(PROG_VERSION, PROG_URL)
    start_t = time.time()

    parser = argparse.ArgumentParser(description = 'Crawl a website searching for issues', epilog = PROG_URL, fromfile_prefix_chars = '@', formatter_class = argparse.RawTextHelpFormatter)
    parser.add_argument('urls', nargs = '+', help = 'list of urls to be checked', type = urlhttp.URLHttp)

    parser.add_argument('--version', action = 'version', version = '%(prog)s {0}'.format(PROG_VERSION), help = 'print %(prog)s version')
    parser.add_argument('-color', action = 'store_true', help = 'enable terminal colors')

    group = parser.add_argument_group('Disable options')
    group.add_argument('-no-robots', action = 'store_true', help = 'ignore websites robots.txt rules (NOT RECOMMENDED)')
    group.add_argument('-no-redirect', action = 'store_true', help = 'ignore website redirection')
    group.add_argument('-no-cookies', action = 'store_true', help = 'ignore website cookies')
    group.add_argument('-no-css', action = 'store_true', help = 'do not extract links from CSS files')

    group = parser.add_argument_group('Validation options')
    group.add_argument('-valid-html', action = 'store_true', help = 'validate HTML online using W3C validator\navailable at https://validator.nu/')
    group.add_argument('-valid-css', action = 'store_true', help = 'validate CSS online using W3C validator\navailable at https://jigsaw.w3.org/css-validator/')
    group.add_argument('-valid-js', action = 'store_true', help = 'validate JavaSript online using Google Closure\navailable at https://closure-compiler.appspot.com/')
    group.add_argument('-valid-result-dir',
        metavar = 'DIR',
        default = 'validation_' + time.strftime('%Y%m%d-%H%M%S', time.gmtime(start_t)) + '{0:.05f}'.format(start_t - int(start_t))[ 1 : ] + 'UTC',
        help = 'directory to save validation results', type = urlutils.normalize_filepath
    )

    group = parser.add_argument_group('Request data')
    group.add_argument('-timeout', metavar = 'SEC', default = 5.0, type = float, help = 'timeout time (seconds) for http requests')
    group.add_argument('-user-agent', metavar = 'UA', default = DEFAULT_UA, help = 'user-agent reported to websites\nalso used to match robots.txt (if enabled)')
    group.add_argument('--cookies',
        nargs = '+', default = [], metavar = 'COOKIE',
        help = textwrap.dedent("""\
            cookies to use (replaced by websites), syntax:
            "NAME=VAL [ ; Path=PATH ] [ ; Domain=DOMAIN ]
            [ ; Max-Age=SECONDS ] [ ; Expires=RFC1123_DATETIME ]
            [ ; HttpOnly ] [ ; Secure ] [ ; ... ]"
        """)
    )
    group.add_argument('--fixed-cookies',
        nargs = '+', default = [], metavar = 'COOKIE',
        help = textwrap.dedent("""\
            cookies to use (replaced by websites), syntax:
            "NAME=VAL [ ; Path=PATH ] [ ; Domain=DOMAIN ]
            [ ; Max-Age=SECONDS ] [ ; Expires=RFC1123_DATETIME ]
            [ ; HttpOnly ] [ ; Secure ] [ ; ... ]"
        """)
    )
    group.add_argument('--headers', nargs = '+', default = [], metavar = 'HEADER', help = 'headers to send, syntax:\n"NAME=VAL"')

    group = parser.add_argument_group('Link matching rules',
        description = textwrap.dedent("""\
            Files should be utf-8
            Special keywords (matches every starting url parameter):
            Format: [*PARAMETER*]
            Available parameters (case sentitive):
                scheme, username, password, hostname, port
                netloc, address, parent, file, path, query
                fragment, request, full
        """)
    )
    group.add_argument('--include-rules',
        nargs = '+', default = [], metavar = 'RULE',
        help = textwrap.dedent("""\
            regex rules to match pages to find urls on
        """)
    )
    group.add_argument('--include-rules-files',
        nargs = '+', default = [], metavar = 'FILE',
        help = textwrap.dedent("""\
            file of regex rules to match pages to find urls on
            one regex per line, lines starting with # are ignored
        """)
    )

    group.add_argument('--exclude-rules',
        nargs = '+', default = [], metavar = 'RULE',
        help = textwrap.dedent("""\
            regex rules to match pages NOT to find urls on
        """)
    )
    group.add_argument('--exclude-rules-files',
        nargs = '+', default = [], metavar = 'FILE',
        help = textwrap.dedent("""\
            file of regex rules to match pages NOT to find urls on
            one regex per line, lines starting with # are ignored
        """)
    )

    args = parser.parse_args()

    Color.enabled = args.color

    start_cookies = urlcookie.CookieJar()
    fixed_cookies = urlcookie.CookieJar()

    errors = {}
    warnings = {}

    urls = urldeque.URLDeque()

    args.headers = { name.title() : value for name, value in ( header.split('=', 1) for header in args.headers ) }
    args.headers['User-Agent'] = args.user_agent
    args.headers.setdefault('Accept-Encoding', 'gzip, deflate')
    args.headers.setdefault('Connection', 'keep-alive')
    args.headers.setdefault('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')

    args.include_rules = args.include_rules or [ r'^https?://[*netloc*].*$' ]

    args.include_rules = urlutils.compile_rules(args.include_rules, args.urls)
    args.exclude_rules = urlutils.compile_rules(args.exclude_rules, args.urls)

    for fname in args.include_rules_files:
        args.include_rules.update(urlutils.read_rules(fname, args.urls))

    for fname in args.exclude_rules_files:
        args.exclude_rules.update(urlutils.read_rules(fname, args.urls))

    if 'Cookie' in args.headers:
        cookies = tuple(map(str.strip, args.headers.pop('Cookie').split(';', 1)))
        for url in args.urls:
            start_cookies.set(url.encoded, *cookies)

    for url in args.urls:
        urls.push(url, url, start_cookies, 'iso-8859-1') # iso-8859-1 = http default

        for cookie in args.cookies:
            start_cookies.set(url.encoded, cookie)

        for cookie in args.fixed_cookies:
            fixed_cookies.set(url.encoded, cookie)

    manager = mp.managers.SyncManager()
    manager.start(lambda: signal.signal(signal.SIGINT, signal.SIG_IGN))

    html_process = None
    html_queue = manager.Queue()
    html_result = manager.dict()
    html_fname = os.path.join(args.valid_result_dir, 'html_result.txt')

    if args.valid_html:
        html_process = mp.Process(target = urlvalidator.URLValidator.thread_html, args = ( html_queue, html_result ))
        html_process.start()

    css_process = None
    css_queue = manager.Queue()
    css_result = manager.dict()
    css_fname = os.path.join(args.valid_result_dir, 'css_result.txt')

    if args.valid_css:
        css_process = mp.Process(target = urlvalidator.URLValidator.thread_css, args = ( css_queue, css_result ))
        css_process.start()

    js_process = None
    js_queue = manager.Queue()
    js_result = manager.dict()
    js_fname = os.path.join(args.valid_result_dir, 'js_result.txt')

    if args.valid_js:
        js_process = mp.Process(target = urlvalidator.URLValidator.thread_js, args = ( js_queue, js_result ))
        js_process.start()

    decompress = {
        'gzip': gzip,
        'x-gzip': gzip,
        'deflate': zlib.decompressobj(wbits = zlib.MAX_WBITS)
    }

    try:
        while not urls.empty:

            url = urlhttp.URLHttp(urls.pop_domain())

            robots = None

            if not args.no_robots:
                robots = urlutils.fetch_robots(url)

                if robots is None:
                    print(Color.RED % 'Could not fetch robots.txt at {0}'.format(url))

            #TODO support proxies
            if url.ssl:
                conn = http.client.HTTPSConnection(url.netloc_encoded, timeout = args.timeout)
            else:
                conn = http.client.HTTPConnection(url.netloc_encoded, timeout = args.timeout)

            try:
                conn.connect()
            except ( socket.error, ConnectionError ):
                while not urls.empty_domain:
                    url, *ignore = urls.pop_url()
                    errors.setdefault(url, []).append('Could not connect to http server')
                continue

            while not urls.empty_domain:

                try:
                    url, ref, cookies, charset = urls.pop_url()

                    if robots is not None and not robots.can_fetch(args.user_agent, url.encoded):
                        print(Color.YELLOW % 'Robot not allowed at {0}'.format(url.full))

                    else:
                        cookies.clear_expired()
                        fixed_cookies.clear_expired()
                        url_cookies = fixed_cookies | cookies

                        request_headers = args.headers.copy()

                        if url_cookies:
                            cookie_txt = '; '.join(map(str, url_cookies.match(url.scheme, url.hostname_encoded, url.path_encoded)))
                            if request_headers.get('Cookie', ''):
                                cookie_txt = request_headers['Cookie'] + '; ' + cookie_txt
                            request_headers['Cookie'] = cookie_txt

                        if ref != url and not 'Referer' in request_headers:
                            request_headers['Referer'] = ref.encoded

                        request = url.request_encoded

                        rep, response_data = urlutils.make_request(conn, 'GET', url.request_encoded, headers = request_headers)

                        if rep is None or rep.status >= 400:
                            new_rep, new_response_data = urlutils.make_request(conn, 'GET', url.request, headers = request_headers)

                            if new_rep is not None and new_rep.status < 400:
                                request = url.request
                                rep = new_rep
                                response_data = new_response_data

                        if rep is None:
                            raise urlutils.URLException('Could not fetch data from server: {0}'.format(response_data))

                        response_headers = urlutils.parse_headers(rep.getheaders())

                        if not args.no_cookies and 'set-cookie' in response_headers:
                            cookies = cookies.copy()
                            cookies.set(url.encoded, *response_headers['set-cookie'])

                        redirect = None

                        if not args.no_redirect and 'location' in response_headers:
                            redirect = url.hyperlink(response_headers['location'][0])
                        else:
                            print((Color.GREEN if rep.status < 300 else Color.YELLOW) % '{0} {1} {2}'.format(url, rep.status, rep.reason))

                            if rep.status >= 300:
                                if rep.status >= 400:
                                    warnings.setdefault(url, []).append('{0} {1}'.format(rep.status, rep.reason))
                                else:
                                    warnings.setdefault(url, []).append('{0} {1} (no redirect location given)'.format(rep.status, rep.reason))

                            include = False

                            for rule in args.include_rules:
                                if rule.search(url.full):
                                    include = True
                                    break

                            if include:
                                for rule in args.exclude_rules:
                                    if rule.search(url.full):
                                        include = False
                                        break

                            if not include:
                                continue

                            content_type = urlutils.content_split(response_headers.get('content-type', [ 'application/octet-stream; charset=iso-8859-1' ])[0])

                            is_html = 'text/html' in content_type or 'application/xhtml+xml' in content_type
                            is_css = 'text/css' in content_type
                            is_js = (
                                'application/javascript' in content_type or
                                'application/x-javascript' in content_type or
                                'text/javascript' in content_type or
                                'application/ecmascript' in content_type or
                                'application/x-ecmascript' in content_type
                            )

                            if is_html or ( is_css and ( not args.no_css or args.valid_css ) ) or ( is_js and args.valid_js ):

                                # TODO accept brotli compression
                                if 'content-encoding' in response_headers:
                                    method = response_headers['content-encoding'][0]
                                    response_data = decompress[method].decompress(response_data)

                                if 'charset' in content_type:
                                    data = response_data.decode(content_type['charset'], errors = 'ignore')
                                    charset = content_type['charset']
                                else:
                                    try:
                                        data = response_data.decode(charset, errors = 'strict')
                                    except ValueError:
                                        data = response_data.decode('iso-8859-1', errors = 'ignore')
                                        charset = 'iso-8859-1'

                                if is_html:
                                    html = urlfinder.URLFinderHTML(data, url, charset)
                                    charset = html.charset

                                    if args.valid_html:
                                        html_queue.put(( url, gzip.compress(response_data), {
                                            'Content-Type': response_headers['content-type'][0],
                                            'Content-Encoding': 'gzip'
                                        } ))

                                    for link, element, attr in html.urls:
                                        if http != 'href' or element['attrs'].get('rel') != 'nofollow':
                                            if not args.no_redirect and element['tag'] == 'meta' and element['attrs'].get('http-equiv', '').lower() == 'refresh' and attr == 'content':
                                                redirect = link
                                            else:
                                                urls.push(link, url, cookies, charset, front = ( element['tag'] != 'a' or attr != 'href' ))

                                elif is_css:

                                    if not args.no_css:
                                        css = urlfinder.URLFinderCSS(data, url, charset)
                                        charset = css.charset

                                        for link in css:
                                            urls.push(link, url, cookies, charset, front = True)

                                    if args.valid_css:
                                        css_queue.put(url)

                                elif is_js:
                                    #TODO parse javascript
                                    if args.valid_js:
                                        js_queue.put(( url, data ))

                        if redirect is not None:
                            try:
                                urls.push_redirect(redirect, url, cookies, charset, front = True)
                            except urldeque.InfiniteRedirection as infinite_redir:
                                print(Color.RED % 'Redirection loop detected!')
                                print(Color.RED % '{0} --> ... --> {1} --> ... --> {0}'.format(url, redirect, url))
                                raise urlutils.URLException(str(infinite_redir))
                            else:
                                print(Color.CYAN % '{0} --> {1}'.format(url, redirect))

                except urlutils.URLException as exc:
                    errors.setdefault(url, []).append(exc.value)

            conn.close()

    except KeyboardInterrupt:
        pass

    if args.valid_html:
        os.makedirs(args.valid_result_dir, exist_ok = True)
        html_queue.put(None)
        html_process.join()

        with open(html_fname, 'w', encoding = 'utf-8') as html_output:
            for url, data in dict(html_result).items():

                if 'messages' in data and len(data['messages']):
                    print(url, file = html_output)

                    warning_count = 0
                    error_count = 0

                    for message in data['messages']:
                        text = '({0})'.format(urlutils.make_gnu_error(message))

                        if 'message' in message:
                            text += ': {0}'.format(message['message'])

                        if message['type'] == 'info':
                            print('-> Warning', text, file = html_output)
                            warning_count += 1
                        else:
                            print('-> Error', text, file = html_output)
                            error_count += 1

                    print(file = html_output)

                    if warning_count > 0:
                        warnings.setdefault(url, []).append('HTML validator: {0}'.format(warning_count))

                    if error_count > 0:
                        errors.setdefault(url, []).append('HTML validator: {0}'.format(error_count))

    if args.valid_css:
        os.makedirs(args.valid_result_dir, exist_ok = True)
        css_queue.put(None)
        css_process.join()

        with open(css_fname, 'w', encoding = 'utf-8') as css_output:
            for url, data in dict(css_result).items():

                if 'cssvalidation' in data:
                    data = data['cssvalidation']

                    warning_count = data['result']['warningcount']
                    error_count = data['result']['errorcount']

                    if warning_count or error_count:

                        if warning_count > 0:
                            warnings.setdefault(url, []).append('CSS validator: {0}'.format(warning_count))

                        if error_count > 0:
                            errors.setdefault(url, []).append('CSS validator: {0}'.format(error_count))

                        print(url, file = css_output)

                        if 'warnings' in data:
                            for warning in data['warnings']:
                                print('-> Warning ({0}):'.format(warning['line']), warning['message'], file = css_output)

                        if 'errors' in data:
                            for error in data['errors']:
                                print('-> Error ({0}):'.format(error['line']), error['message'], file = css_output)

                        print(file = css_output)

    if args.valid_js:
        os.makedirs(args.valid_result_dir, exist_ok = True)
        js_queue.put(None)
        js_process.join()

        with open(js_fname, 'w', encoding = 'utf-8') as js_output:
            for url, data in dict(js_result).items():

                warning_count = len(data.setdefault('warnings', []))
                error_count = len(data.setdefault('errors', []))

                if warning_count or error_count:

                    if warning_count > 0:
                        warnings.setdefault(url, []).append('JavaScript validator: {0}'.format(warning_count))

                    if error_count > 0:
                        errors.setdefault(url, []).append('JavaScript validator: {0}'.format(error_count))

                    print(url, file = js_output)

                    for warning in data['warnings']:
                        print('-> Warning ({0}.{1}):'.format(warning['lineno'], warning['charno']), warning['warning'], file = js_output)

                    for error in data['errors']:
                        print('-> Error ({0}.{1}):'.format(error['lineno'], error['charno']), error['error'], file = js_output)

                    print(file = js_output)

    issues = set(errors.keys() | warnings.keys())

    if issues:
        print((Color.RED if errors else Color.YELLOW) % '\n{0} urls with issues found!'.format(len(issues)))
        for url in issues:
            url_warnings = warnings.get(url, [])
            url_errors = errors.get(url, [])

            print((Color.RED if url_errors else Color.YELLOW) % '\n{0}'.format(url))

            for warning in url_warnings:
                print(Color.YELLOW % 'Warning: {0}'.format(warning))

            for error in url_errors:
                print(Color.RED % 'Error: {0}'.format(error))

            print('Referenced by:')
            for page in urls.references(url):
                print('-> {0}'.format(page))

    if args.valid_html:
        print('\nHTML validation issues saved to {0}'.format(html_fname))

    if args.valid_css:
        print('\nCSS validation issues saved to {0}'.format(css_fname))

    if args.valid_js:
        print('\nJavaScript validation issues saved to {0}'.format(js_fname))
