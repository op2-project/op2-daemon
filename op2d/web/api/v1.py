
import platform
import traceback

from flask import Flask, abort, json, request
from sipsimple.account import Account, BonjourAccount, AccountManager
from sipsimple.configuration import DefaultValue, DuplicateIDError
from sipsimple.configuration.settings import SIPSimpleSettings
from sipsimple.core import Engine

import op2d

__all__ = ['app']


app = Flask('api_v1')


def get_state(obj):
    def cleanup_state(o, old_state):
        state = {}
        for k, v in old_state.iteritems():
            if v is DefaultValue:
                v = getattr(o, k)
            elif isinstance(v, dict):
                v = cleanup_state(getattr(o, k), v)
            if hasattr(v, '__getstate__'):
                v = v.__getstate__()
            if v in ('true', 'false'):
                # fix booleans to be real booleans and not strings
                v = True if v=='true' else False
            state[k] = v
        return state
    return cleanup_state(obj, obj.__getstate__())


def set_state(obj, state):
    valid_keys = dir(obj.__class__)
    for k, v in ((k, v) for k, v in state.iteritems() if k in valid_keys):
        if isinstance(v, dict):
            o = getattr(obj, k, None)
            if o is not None:
                set_state(o, v)
        else:
            setattr(obj, k, v)


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
        except Exception:
            traceback.print_exc()
        account.enabled = True
        account.save()
        return json.jsonify(get_state(account)), 201


@app.route('/accounts/<account_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_account(account_id):
    try:
        account = AccountManager().get_account(account_id)
    except KeyError:
        abort(404)

    if request.method == 'GET':
        # Retrieve account
        return json.jsonify({'account': get_state(account)})
    elif request.method == 'PUT':
        # Update existing account
        state = request.get_json(silent=True)
        if not state:
            abort(400)
        state.pop('id', None)
        try:
            set_state(account, state)
        except Exception:
            traceback.print_exc()
            abort(400)
        account.save()
        return json.jsonify({'account': get_state(account)})
    elif request.method == 'DELETE':
        try:
            account.delete()
        except Exception:
            abort(400)
        return ''


@app.route('/accounts/<account_id>/reregister')
def reregister_account(account_id):
    try:
        account = AccountManager().get_account(account_id)
    except KeyError:
        abort(404)
    if account is BonjourAccount():
        abort(403)
    account.reregister()
    return ''


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
        except Exception:
            traceback.print_exc()
            abort(400)
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


