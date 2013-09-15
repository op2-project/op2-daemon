
import platform

from application import log
from flask import Flask, abort, json, request
from sipsimple.account import Account, BonjourAccount, AccountManager
from sipsimple.configuration import DuplicateIDError
from sipsimple.configuration.settings import SIPSimpleSettings
from sipsimple.core import Engine
from sipsimple.streams import AudioStream
from werkzeug.routing import BaseConverter

import op2d

from op2d.accounts import AccountModel
from op2d.sessions import SessionManager
from op2d.web.api.utils import get_state, set_state

__all__ = ['app']


app = Flask('api_v1')


class SipUriConverter(BaseConverter):
    regex = '.*?'
    weight = 300

app.url_map.converters['sip'] = SipUriConverter


@app.route('/')
def index():
    message = 'OP2d version %s APIv1' % op2d.__version__
    return json.jsonify({'message': message})


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
            state['auth']['password'] = '****'
            accs.append(state)
        return json.jsonify({'accounts': accs})
    elif request.method == 'POST':
        # Create account
        state = request.get_json(silent=True)
        if not state:
            abort(400)
        account_id = state.pop('id', None)
        if not account_id:
            abort(400)
        try:
            account = Account(account_id)
        except DuplicateIDError:
            abort(409)
        try:
            set_state(account, state)
        except ValueError, e:
            account.delete()
            return json.jsonify({'msg': str(e)}), 400
        account.enabled = True
        account.save()
        state = get_state(account)
        state['auth']['password'] = '****'
        return json.jsonify({'account': state}), 201


@app.route('/accounts/<sip:account_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_account(account_id):
    try:
        account = AccountManager().get_account(account_id)
    except KeyError:
        abort(404)

    if request.method == 'GET':
        # Retrieve account
        state = get_state(account)
        state['auth']['password'] = '****'
        return json.jsonify({'account': state})
    elif request.method == 'PUT':
        # Update existing account
        state = request.get_json(silent=True)
        if not state:
            abort(400)
        state.pop('id', None)
        try:
            set_state(account, state)
        except ValueError, e:
            return json.jsonify({'msg': str(e)}), 400
        account.save()
        state = get_state(account)
        state['auth']['password'] = '****'
        return json.jsonify({'account': state})
    elif request.method == 'DELETE':
        try:
            account.delete()
        except Exception:
            abort(400)
        return ''


@app.route('/accounts/<sip:account_id>/reregister')
def reregister_account(account_id):
    try:
        account = AccountManager().get_account(account_id)
    except KeyError:
        abort(404)
    if account is BonjourAccount():
        abort(403)
    account.reregister()
    return ''


@app.route('/accounts/<sip:account_id>/info')
def account_info(account_id):
    try:
        account = AccountManager().get_account(account_id)
    except KeyError:
        abort(404)
    model = AccountModel()
    registration = {}
    info = model.get_account(account.id)
    if info is not None:
        registration['state'] = info.registration_state
        registration['registrar'] = info.registrar
    else:
        registration['state'] = 'unknown'
        registration['registrar'] = None
    return json.jsonify({'info': {'registration': registration}})


# General settings management

@app.route('/settings', methods=['GET', 'PUT'])
def handle_settings():
    settings = SIPSimpleSettings()
    if request.method == 'GET':
        # Retrieve settings
        return json.jsonify(get_state(settings))
    else:
        # Update settings
        state = request.get_json(silent=True)
        if not state:
            abort(400)
        try:
            set_state(settings, state)
        except ValueError, e:
            return json.jsonify({'msg': str(e)}), 400
        settings.save()
        return json.jsonify(get_state(settings))


# System information

@app.route('/system/info')
def system_info():
    info = {}
    info['machine_type'] = platform.machine()
    info['network_name'] = platform.node()
    info['python_version'] = platform.python_version()
    info['platform'] = platform.platform()
    return json.jsonify({'info': info})


@app.route('/system/audio_codecs')
def audio_codecs():
    engine = Engine()
    return json.jsonify({'audio_codecs': engine.available_codecs})


@app.route('/system/audio_devices')
def audio_devices():
    engine = Engine()
    devices = {'input': None, 'output': None}
    devices['input'] = engine.input_devices
    devices['output'] = engine.output_devices
    return json.jsonify({'devices': devices})


# Sessions

@app.route('/sessions/dial')
def dial():
    to = request.args.get('to', None)
    if to is None:
        abort(400)
    account_id = request.args.get('from', None)
    account = None
    if account_id is not None:
        try:
            account = AccountManager().get_account(account_id)
        except KeyError:
            pass
    try:
        SessionManager().start_call(None, to, [AudioStream()], account=account)
    except Exception:
        log.error('Starting call to %s' % to)
        log.err()
        abort(400)
    return ''

