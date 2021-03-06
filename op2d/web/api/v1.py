
import platform

from application import log
from flask import Flask, request, send_file
from sipsimple.account import Account, BonjourAccount, AccountManager
from sipsimple.configuration import DuplicateIDError
from sipsimple.configuration.settings import SIPSimpleSettings
from sipsimple.core import Engine
from sipsimple.threading import run_in_thread
from werkzeug.routing import BaseConverter

import op2d

from op2d.accounts import AccountModel
from op2d.history import HistoryManager
from op2d.resources import ApplicationData
from op2d.sessions import SessionManager
from op2d.tracing import TraceManager
from op2d.web.api.utils import error_response, get_state, get_json, jsonify, set_state

__all__ = ['app']


app = Flask(__name__)


class SipUriConverter(BaseConverter):
    regex = '.*?'
    weight = 300

app.url_map.converters['sip'] = SipUriConverter


@app.errorhandler(404)
def not_found(error):
    return jsonify({'msg': 'resource not found'}), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify({'msg': 'internal server error'}), 500


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
        state = get_json(request)
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
        state = get_json(request)
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
        state = get_json(request)
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


@app.route('/system/refresh_audio_devices')
def refresh_audio_devices():
    engine = Engine()
    engine.refresh_sound_devices()
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
        session_manager = SessionManager()
        session_manager.start_call(None, to, account=account)
    except Exception, e:
        log.error('Starting call to %s: %s' % (to, e))
        log.err()
        return error_response(400, str(e))
    return ''


# History

@app.route('/history')
def history():
    history_manager = HistoryManager()
    entries = []
    for entry in history_manager.calls:
        if entry.name:
            caller = '%s <%s>' % (entry.name, entry.uri)
        else:
            caller = entry.uri
        entries.append(dict(direction=entry.direction,
                            caller=caller,
                            account=entry.account_id,
                            call_time=str(entry.call_time.replace(microsecond=0)),
                            duration=entry.duration.total_seconds() if entry.duration is not None else 0,
                            failure=None if not entry.failed else entry.reason,
                            text=entry.text))
    return jsonify({'history': entries})


# Logs

@app.route('/logs/<logfile>', methods=['GET', 'DELETE'])
def logs(logfile):
    if logfile not in ('sip', 'msrp', 'pjsip', 'notifications'):
        return error_response(404, 'invalid log file')

    if request.method == 'GET':
        try:
            return send_file(ApplicationData.get('logs/%s.log' % logfile))
        except Exception as e:
            return error_response(500, str(e))
    elif request.method == 'DELETE':
        @run_in_thread('file-io')
        def delete_file(logfile):
            trace_manager = TraceManager()
            if logfile == 'sip':
                trace_manager.siptrace_file.truncate()
            elif logfile == 'pjsip':
                trace_manager.pjsiptrace_file.truncate()
            elif logfile == 'msrp':
                trace_manager.msrptrace_file.truncate()
            elif logfile == 'notifications':
                trace_manager.notifications_file.truncate()
        delete_file(logfile)
        return ''

