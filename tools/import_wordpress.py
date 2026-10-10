"""One-off importer: turns the downloaded WordPress HTML into clean static pages.

Usage:  python tools/import_wordpress.py <raw-dir>

<raw-dir> must contain html/*.html (pages as served by the live site),
uploads/ (a mirror of wp-content/uploads), css/ (the theme/plugin stylesheets),
fonts/, img/ (Flatsome theme images) and imaps_app.min.js (map plugin).
It overwrites the page files and assets. After importing, run tools/build.py
to inject the shared header/footer. Needs beautifulsoup4.

The import was done once (September 2026); from now on edit the HTML directly.
"""
import hashlib
import os
import re
import shutil
import sys
from bs4 import BeautifulSoup, Comment

RAW = sys.argv[1]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://escapegamethehunt.nl'

UPLOADS_ABS = SITE + '/assets/uploads/'
UPLOADS_RE = re.compile(r'https?:(\\?/)(\\?/)escapegamethehunt\.nl\\?/wp-content\\?/uploads\\?/')
NOISE_ATTRS = {'data-start', 'data-end', 'data-is-last-node', 'data-is-only-node',
               'data-message-author-role', 'data-message-id', 'data-section-id', 'data-col-size'}
PLACEHOLDER_SRC = 'data:image/svg+xml'


def url_to_path(url):
    path = re.sub(r'^https?://escapegamethehunt\.nl', '', url) or '/'
    return path if path.endswith('/') else path + '/'


def local_link(href):
    """Make links to the live site root-relative so they work on any host."""
    m = re.match(r'^https?://(www\.)?escapegamethehunt\.nl(/.*)?$', href)
    if not m:
        return href
    # WordPress redirects .../page/1/ to the first archive page
    return re.sub(r'page/1/$', '', m.group(2) or '/')


def fix_uploads(text, absolute=False):
    repl = UPLOADS_ABS if absolute else '/assets/uploads/'
    def sub(m):
        return repl.replace('/', '\\/') if m.group(1) == '\\/' else repl
    return UPLOADS_RE.sub(sub, text)


def clean_main(main, report):
    for c in main.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    for t in main.find_all(True):
        for a in list(t.attrs):
            if a in NOISE_ATTRS:
                del t[a]
    # Lazy-loaded images (W3 Total Cache) -> real src + native lazy loading
    for img in main.find_all('img'):
        if img.get('data-src'):
            img['src'] = img['data-src']
            del img['data-src']
        elif img.get('src', '').startswith(PLACEHOLDER_SRC):
            report.append('image without real src')
        for a in ('srcset', 'sizes'):
            if img.get('data-' + a):
                img[a] = img['data-' + a]
                del img['data-' + a]
        if img.get('class'):
            img['class'] = [c for c in img['class'] if c != 'lazy'] or None
            if img['class'] is None:
                del img['class']
        if img.get('fetchpriority') != 'high':
            img['loading'] = 'lazy'
        img['decoding'] = 'async'
    for f in main.find_all('iframe'):
        f['loading'] = 'lazy'
    for a in main.find_all('a', href=True):
        a['href'] = local_link(a['href'])
    # HappyForms: strip the WordPress-only plumbing, keep the fields
    for form in main.select('form[id^=happyforms-form]'):
        form['action'] = ''
        form['data-static-form'] = ''
        for name in ('happyforms_random_seed', 'action', 'client_referer', 'current_post_id',
                     'happyforms_form_id', 'happyforms_step'):
            for i in form.find_all('input', attrs={'name': name}):
                i.decompose()
        for i in form.find_all('input', attrs={'name': re.compile(r'^\d+-single_line_text$')}):
            i['data-honeypot'] = ''
        for part in form.select('.happyforms-part--recaptcha'):
            part.decompose()
        # Default date was the date of scraping; let the browser start empty
        for d in form.select('input[type=date]'):
            if d.has_attr('value'):
                del d['value']
    for l in main.find_all('link', rel='stylesheet'):
        l.decompose()  # plugin CSS is linked from <head> instead
    for s in main.find_all('script'):
        report.append('script in content removed: ' + (s.get('src') or (s.string or '')[:40]))
        s.decompose()


def head_meta(soup):
    out = []
    title = soup.title.string.strip() if soup.title and soup.title.string else 'Escape Game The Hunt'
    out.append('<title>%s</title>' % BeautifulSoup(title, 'html.parser').decode(formatter='html'))
    for m in soup.head.find_all('meta'):
        name = m.get('name') or m.get('property') or ''
        if name in ('description', 'robots') or name.startswith(('og:', 'twitter:', 'article:')):
            if name in ('og:updated_time',):
                continue
            m2 = BeautifulSoup(str(m), 'html.parser').meta
            if m2.get('content'):
                m2['content'] = fix_uploads(m2['content'], absolute=True)
            out.append(str(m2))
    canon = soup.head.find('link', rel='canonical')
    if canon:
        out.append('<link rel="canonical" href="%s">' % canon['href'])
    for rel in ('prev', 'next'):
        l = soup.head.find('link', rel=rel)
        if l:
            out.append('<link rel="%s" href="%s">' % (rel, local_link(l['href'])))
    ld = soup.head.find('script', type='application/ld+json')
    if ld and ld.string:
        out.append('<script type="application/ld+json">%s</script>' % fix_uploads(ld.string.strip(), absolute=True))
    return '\n'.join(out)


def main():
    pages = []
    report = {}
    header_variants = {}
    for fn in sorted(os.listdir(os.path.join(RAW, 'html'))):
        with open(os.path.join(RAW, 'html', fn), encoding='utf-8') as fh:
            html = fh.read()
        soup = BeautifulSoup(html, 'html.parser')
        canon = soup.head.find('link', rel='canonical')
        path = url_to_path(canon['href']) if canon else '/'
        rep = report.setdefault(path, [])

        header = soup.find('header', id='header')
        header_classes = ' '.join(header.get('class', []))
        h = BeautifulSoup(str(header), 'html.parser')
        for li in h.find_all('li'):
            li['class'] = [c for c in li.get('class', []) if c not in (
                'active', 'current-menu-item', 'current_page_item', 'current-menu-ancestor',
                'current-menu-parent', 'current_page_parent', 'current_page_ancestor')]
        for a in h.find_all('a'):
            if a.has_attr('aria-current'):
                del a['aria-current']
        inner = h.header.decode_contents()
        key = hashlib.md5(re.sub(r'\s+', ' ', inner).encode()).hexdigest()[:8]
        header_variants.setdefault(key, []).append(path)

        main_el = soup.find('main', id='main')
        clean_main(main_el, rep)
        content = fix_uploads(main_el.decode_contents())

        body_classes = [c for c in soup.body.get('class', [])
                        if not re.match(r'(wp-theme|wp-child-theme|wp-singular|page-id-|postid-|parent-pageid-|category-\d+)', c)]
        extras = set()
        if 'happyforms-form' in content:
            extras.add('happyforms')
        if 'ez-toc-container' in content:
            extras.add('eztoc')
        if 'ux-timer' in content:
            extras.add('countdown')
        imaps = ''
        if 'map_box' in content:
            extras.add('imaps')
            for s in soup.find_all('script'):
                if s.string and s.string.lstrip().startswith('var iMapsData'):
                    imaps = fix_uploads(s.string.strip(), absolute=True)
        pages.append(dict(path=path, head=head_meta(soup), body_class=' '.join(body_classes),
                          header_class=header_classes, content=content, extras=sorted(extras),
                          imaps=imaps))

    print('header variants:', {k: len(v) for k, v in header_variants.items()})
    for k, v in header_variants.items():
        if len(v) < 5:
            print('  ', k, v)

    for p in pages:
        write_page(p)
    for path, rep in report.items():
        for r in sorted(set(rep)):
            print('NOTE', path, r)
    copy_assets()
    print(len(pages), 'pages written')


def write_page(p):
    css = ['<link rel="stylesheet" href="/assets/css/flatsome.css">',
           '<link rel="stylesheet" href="/assets/css/theme.css">',
           '<link rel="stylesheet" href="/assets/css/site.css">']
    js = []
    if 'happyforms' in p['extras']:
        css.append('<link rel="stylesheet" href="/assets/css/happyforms.css">')
    if 'eztoc' in p['extras']:
        css.append('<link rel="stylesheet" href="/assets/css/eztoc.css">')
    if 'countdown' in p['extras']:
        css.append('<link rel="stylesheet" href="/assets/css/ux-countdown.css">')
    if 'imaps' in p['extras']:
        css.append('<link rel="stylesheet" href="/assets/css/imaps.css">')
        js += ['<script src="https://cdn.amcharts.com/lib/version/4.10.29/core.js"></script>',
               '<script src="https://cdn.amcharts.com/lib/version/4.10.29/maps.js"></script>',
               '<script src="https://cdn.amcharts.com/lib/version/4.10.29/themes/animated.js"></script>',
               '<script src="https://cdn.amcharts.com/lib/4/geodata/netherlandsHigh.js"></script>',
               '<script>\n%s\n</script>' % p['imaps'],
               '<script src="/assets/js/imaps/app.min.js"></script>']
    html = f'''<!doctype html>
<html lang="nl-NL" class="no-js">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{p['head']}
<link rel="icon" href="/assets/uploads/2025/05/cropped-escapegamethehunt-512-32x32.png" sizes="32x32">
<link rel="icon" href="/assets/uploads/2025/05/cropped-escapegamethehunt-512-192x192.png" sizes="192x192">
<link rel="apple-touch-icon" href="/assets/uploads/2025/05/cropped-escapegamethehunt-512-180x180.png">
<link rel="preload" href="/assets/fonts/S6uyw4BMUTPHjx4wXg.woff2" as="font" type="font/woff2" crossorigin>
{chr(10).join(css)}
</head>
<body class="{p['body_class']}">
<a class="skip-link screen-reader-text" href="#main">Ga naar inhoud</a>
<div id="wrapper">
<header id="header" class="{p['header_class']}">
<!-- partial:header -->
<!-- /partial:header -->
</header>
<main id="main">
{p['content'].strip()}
</main>
<!-- partial:footer -->
<!-- /partial:footer -->
</div>
<!-- partial:mobile-menu -->
<!-- /partial:mobile-menu -->
<script src="/assets/js/site.js" defer></script>
{chr(10).join(js)}
</body>
</html>
'''
    out = os.path.join(ROOT, *p['path'].strip('/').split('/'), 'index.html') if p['path'] != '/' \
        else os.path.join(ROOT, 'index.html')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(html)


FONT_FACES = '''/* Lato + Dancing Script (self-hosted, latin + latin-ext) */
@font-face{font-family:'Lato';font-style:normal;font-weight:400;font-display:swap;src:url(../fonts/S6uyw4BMUTPHjxAwXjeu.woff2) format('woff2');unicode-range:U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF}
@font-face{font-family:'Lato';font-style:normal;font-weight:400;font-display:swap;src:url(../fonts/S6uyw4BMUTPHjx4wXg.woff2) format('woff2');unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}
@font-face{font-family:'Lato';font-style:normal;font-weight:700;font-display:swap;src:url(../fonts/S6u9w4BMUTPHh6UVSwaPGR_p.woff2) format('woff2');unicode-range:U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF}
@font-face{font-family:'Lato';font-style:normal;font-weight:700;font-display:swap;src:url(../fonts/S6u9w4BMUTPHh6UVSwiPGQ.woff2) format('woff2');unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}
@font-face{font-family:'Dancing Script';font-style:normal;font-weight:400;font-display:swap;src:url(../fonts/If2cXTr6YS-zF4S-kcSWSVi_sxjsohD9F50Ruu7BMSo3ROp8ltA.woff2) format('woff2');unicode-range:U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF}
@font-face{font-family:'Dancing Script';font-style:normal;font-weight:400;font-display:swap;src:url(../fonts/If2cXTr6YS-zF4S-kcSWSVi_sxjsohD9F50Ruu7BMSo3Sup8.woff2) format('woff2');unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}
/* Flatsome icon font */
@font-face{font-family:"fl-icons";font-display:block;src:url(../fonts/fl-icons.woff2) format("woff2"),url(../fonts/fl-icons.woff) format("woff"),url(../fonts/fl-icons.ttf) format("truetype")}
'''


def write_theme_css():
    """theme.css: the inline <head> styles WordPress printed on every page."""
    with open(os.path.join(RAW, 'html', 'escaperoom-assen.html'), encoding='utf-8') as fh:
        head = BeautifulSoup(fh.read(), 'html.parser').head

    def style(id_):
        t = head.find('style', id=id_)
        return re.sub(r'/\*# sourceURL=.*?\*/', '', t.string).strip() if t else ''

    css = '\n'.join([
        '/* Theme styles taken over from the WordPress site (Flatsome customizer, block library, custom CSS). */',
        FONT_FACES,
        '/* WordPress block library */', style('wp-block-library-inline-css'),
        '/* WordPress global styles */', style('global-styles-inline-css'),
        '/* Flatsome customizer */', style('custom-css'),
        '/* Custom CSS (WordPress "Extra CSS") */', style('wp-custom-css'),
    ]) + '\n'
    with open(os.path.join(ROOT, 'assets', 'css', 'theme.css'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(css)
    with open(os.path.join(ROOT, 'assets', 'css', 'eztoc.css'), 'a', encoding='utf-8', newline='\n') as fh:
        fh.write('\n' + style('eztoc-inline-css') + '\n')


def copy_assets():
    a = os.path.join(ROOT, 'assets')
    shutil.copytree(os.path.join(RAW, 'img'), os.path.join(a, 'img'), dirs_exist_ok=True)
    for d in ('css', 'fonts', 'js/imaps'):
        os.makedirs(os.path.join(a, d), exist_ok=True)
    shutil.copytree(os.path.join(RAW, 'uploads'), os.path.join(a, 'uploads'), dirs_exist_ok=True)
    for f in os.listdir(os.path.join(RAW, 'fonts')):
        shutil.copy(os.path.join(RAW, 'fonts', f), os.path.join(a, 'fonts', f))
    shutil.copy(os.path.join(RAW, 'imaps_app.min.js'), os.path.join(a, 'js', 'imaps', 'app.min.js'))
    for src, dst in (('css_flatsome.css', 'flatsome.css'), ('css_frontend.css', 'happyforms.css'),
                     ('css_screen.min.css', 'eztoc.css'), ('css_styles.min.css', 'imaps.css'),
                     ('ux_countdown_ux-countdown.css', 'ux-countdown.css')):
        shutil.copy(os.path.join(RAW, 'css', src), os.path.join(a, 'css', dst))
    write_theme_css()


if __name__ == '__main__':
    main()
