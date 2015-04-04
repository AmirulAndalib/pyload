# -*- coding: utf-8 -*-
# @author: RaNaN, vuolter

import sys
import pyload.utils.pylgettext as gettext

import os
from os.path import join, abspath, dirname, exists
from os import makedirs

THEME_DIR  = abspath(join(dirname(__file__), "themes"))
PYLOAD_DIR = abspath(join(THEME_DIR, "..", "..", ".."))

sys.path.append(PYLOAD_DIR)

from pyload.utils import decode, formatSize

import bottle
from bottle import run, app

from jinja2 import Environment, FileSystemLoader, PrefixLoader, FileSystemBytecodeCache
from middlewares import StripPathMiddleware, GZipMiddleWare, PrefixMiddleware

SETUP = None
PYLOAD = None

from pyload.manager.thread import Server
from pyload.network.JsEngine import JsEngine

if not Server.core:
    if Server.setup:
        SETUP = Server.setup
        config = SETUP.config
        JS = JsEngine(SETUP)
    else:
        raise Exception("Could not access pyLoad Core")
else:
    PYLOAD = Server.core.api
    config = Server.core.config
    JS = JsEngine(Server.core)

THEME = config.get('webinterface', 'theme')
DL_ROOT = config.get('general', 'download_folder')
LOG_ROOT = config.get('log', 'log_folder')
PREFIX = config.get('webinterface', 'prefix')

if PREFIX:
    PREFIX = PREFIX.rstrip("/")
    if not PREFIX.startswith("/"):
        PREFIX = "/" + PREFIX

DEBUG = config.get("general", "debug_mode") or "-d" in sys.argv or "--debug" in sys.argv
bottle.debug(DEBUG)

cache = join("tmp", "jinja_cache")
if not exists(cache):
    makedirs(cache)

bcc = FileSystemBytecodeCache(cache, '%s.cache')

loader = FileSystemLoader([THEME_DIR, join(THEME_DIR, THEME)])

env = Environment(loader=loader, extensions=['jinja2.ext.i18n', 'jinja2.ext.autoescape'], trim_blocks=True, auto_reload=False,
                  bytecode_cache=bcc)

from filters import quotepath, path_make_relative, path_make_absolute, truncate, date

env.filters["quotepath"] = quotepath
env.filters["truncate"] = truncate
env.filters["date"] = date
env.filters["path_make_relative"] = path_make_relative
env.filters["path_make_absolute"] = path_make_absolute
env.filters["decode"] = decode
env.filters["type"] = lambda x: str(type(x))
env.filters["formatsize"] = formatSize
env.filters["getitem"] = lambda x, y: x.__getitem__(y)
if PREFIX:
    env.filters["url"] = lambda x: x
else:
    env.filters["url"] = lambda x: PREFIX + x if x.startswith("/") else x

gettext.setpaths([join(os.sep, "usr", "share", "pyload", "locale"), None])
translation = gettext.translation("django", join(PYLOAD_DIR, "locale"),
    languages=[config.get("general", "language"), "en"],fallback=True)
translation.install(True)
env.install_gettext_translations(translation)

from beaker.middleware import SessionMiddleware

session_opts = {
    'session.type': 'file',
    'session.cookie_expires': False,
    'session.data_dir': './tmp',
    'session.auto': False
}

web = StripPathMiddleware(SessionMiddleware(app(), session_opts))
web = GZipMiddleWare(web)

if PREFIX:
    web = PrefixMiddleware(web, prefix=PREFIX)

import pyload.webui.app

def run_simple(host="0.0.0.0", port="8000"):
    run(app=web, host=host, port=port, quiet=True)


def run_lightweight(host="0.0.0.0", port="8000"):
    run(app=web, host=host, port=port, server="bjoern", quiet=True)


def run_threaded(host="0.0.0.0", port="8000", theads=3, cert="", key=""):
    from wsgiserver import CherryPyWSGIServer

    if cert and key:
        CherryPyWSGIServer.ssl_certificate = cert
        CherryPyWSGIServer.ssl_private_key = key

    CherryPyWSGIServer.numthreads = theads

    from pyload.webui.app.utils import CherryPyWSGI

    run(app=web, host=host, port=port, server=CherryPyWSGI, quiet=True)


def run_fcgi(host="0.0.0.0", port="8000"):
    from bottle import FlupFCGIServer

    run(app=web, host=host, port=port, server=FlupFCGIServer, quiet=True)
