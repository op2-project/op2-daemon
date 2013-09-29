
import platform

from application import log
from flask import Flask, json, request
from sipsimple.account import Account, BonjourAccount, AccountManager
from sipsimple.configuration import DuplicateIDError
from sipsimple.configuration.settings import SIPSimpleSettings
from sipsimple.core import Engine
from sipsimple.streams import AudioStream
from werkzeug.routing import BaseConverter

try:
    from flask.json import jsonify
except ImportError:
    from flask.helpers import jsonify

import op2d

from op2d.accounts import AccountModel
from op2d.sessions import SessionManager
from op2d.web.api.utils import error_response, get_state, set_state

__all__ = ['app']


app = Flask(__name__)


class SipUriConverter(BaseConverter):
    regex = '.*?'
    weight = 300

app.url_map.converters['sip'] = SipUriConverter


@app.errorhandler(404)
def not_found(error):
    return jsonify({'msg': 'resource not found'}), 404


@app.route('/')
def index():
    message = 'OP2d version %s APIv1' % op2d.__version__
    return jsonify({'message': message})


# Account management

@app.route('/accounts', methods=['GET', 'POST'])
def handle_accounts():
    if request.method == 'GET':
        # Retrieve accounts list
        accounts = AccountManager().get_accounts()
        accs = []
        for account in accounts:
            state = get_state(account)
            state['id'] = account.id
            if 'auth' in state:
                state['auth']['password'] = '****'
            accs.append(state)
        return jsonify({'accounts': accs})
    elif request.method == 'POST':
        # Create account
        state = request.get_json(silent=True)
        if not state:
            return error_response(400, 'error processing POST body')
        account_id = state.pop('id', None)
        if not account_id:
            return error_response(400, 'account ID was not specified')
        try:
            account = Account(account_id)
        except DuplicateIDError:
            return error_response(409, 'duplicated account ID')
        try:
            set_state(account, state)
        except ValueError, e:
            account.delete()
            return error_response(400, str(e))
        account.enabled = True
        account.save()
        state = get_state(account)
        if 'auth' in state:
            state['auth']['password'] = '****'
        return jsonify({'account': state}), 201


@app.route('/accounts/<sip:account_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_account(account_id):
    try:
        account = AccountManager().get_account(account_id)
    except KeyError:
        return error_response(404, 'account not found')

    if request.method == 'GET':
        # Retrieve account
        state = get_state(account)
        if 'auth' in state:
            state['auth']['password'] = '****'
        return jsonify({'account': state})
    elif request.method == 'PUT':
        # Update existing account
        state = request.get_json(silent=True)
        if not state:
            return error_response(400, 'error processing PUT body')
        state.pop('id', None)
        try:
            set_state(account, state)
        except ValueError, e:
            # TODO: some settings may have been applied, what do we do?
            return error_response(400, str(e))
        account.save()
        state = get_state(account)
        if 'auth' in state:
            state['auth']['password'] = '****'
        return jsonify({'account': state})
    elif request.method == 'DELETE':
        try:
            account.delete()
        except Exception, e:
            return error_response(400, str(e))
        return ''


@app.route('/accounts/<sip:account_id>/reregister')
def reregister_account(account_id):
    try:
        account = AccountManager().get_account(account_id)
    except KeyError:
        return error_response(404, 'account not found')
    if account is BonjourAccount():
        return error_response(403, 'bonjour account does not register')
    account.reregister()
    return ''


@app.route('/accounts/<sip:account_id>/info')
def account_info(account_id):
    try:
        account = AccountManager().get_account(account_id)
    except KeyError:
        return error_response(404, 'account not found')
    model = AccountModel()
    registration = {}
    info = model.get_account(account.id)
    if info is not None:
        registration['state'] = info.registration_state
        registration['registrar'] = info.registrar
    else:
        registration['state'] = 'unknown'
        registration['registrar'] = None
    return jsonify({'info': {'registration': registration}})


# General settings management

@app.route('/settings', methods=['GET', 'PUT'])
def handle_settings():
    settings = SIPSimpleSettings()
    if request.method == 'GET':
        # Retrieve settings
        return jsonify(get_state(settings))
    else:
        # Update settings
        state = request.get_json(silent=True)
        if not state:
            return error_response(400, 'error processing PUT body')
        try:
            set_state(settings, state)
        except ValueError, e:
            # TODO: some settings may have been applied, what do we do?
            return error_response(400, str(e))
        settings.save()
        return jsonify(get_state(settings))


# System information

@app.route('/system/info')
def system_info():
    info = {}
    info['machine_type'] = platform.machine()
    info['network_name'] = platform.node()
    info['python_version'] = platform.python_version()
    info['platform'] = platform.platform()
    return jsonify({'info': info})


@app.route('/system/audio_codecs')
def audio_codecs():
    engine = Engine()
    return jsonify({'audio_codecs': engine.available_codecs})


@app.route('/system/audio_devices')
def audio_devices():
    engine = Engine()
    devices = {'input': ['system_default', None], 'output': ['system_default', None]}
    devices['input'].extend(engine.input_devices)
    devices['output'].extend(engine.output_devices)
    return jsonify({'devices': devices})


# Sessions

@app.route('/sessions/dial')
def dial():
    to = request.args.get('to', None)
    if to is None:
        return error_response(400, 'destionation not specified')
    account_id = request.args.get('from', None)
    account = None
    if account_id is not None:
        try:
            account = AccountManager().get_account(account_id)
        except KeyError:
            return error_response(400, 'invalid account specified')
    try:
        SessionManager().start_call(None, to, [AudioStream()], account=account)
    except Exception, e:
        log.error('Starting call to %s: %s' % (to, e))
        log.err()
        return error_response(400, str(e))
    return ''

