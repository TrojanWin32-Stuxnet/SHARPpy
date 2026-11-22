"""Offline regressions for availability failures before the picker is shown."""

from datetime import datetime
from http.client import IncompleteRead
from pathlib import Path
import socket
import xml.etree.ElementTree as ET

import pytest


class Response:
    def __init__(self, body=b'', error=None):
        self.body = body
        self.error = error
        self.closed = False

    def read(self):
        if self.error is not None:
            raise self.error
        return self.body

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


@pytest.fixture(scope='module')
def startup_modules(tmp_path_factory):
    # Imports initialize user resources and logging. Keep those in a test home.
    home = tmp_path_factory.mktemp('startup-home')
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv('USERPROFILE', str(home))
        patch.setenv('HOME', str(home))
        patch.setenv('QT_QPA_PLATFORM', 'offscreen')
        from runsharp import full_gui
        from datasources import data_source

        app = full_gui.QApplication.instance() or full_gui.QApplication([])
        yield full_gui, data_source
        app.quit()


@pytest.fixture
def observed(startup_modules, monkeypatch):
    gui, sources = startup_modules
    resource_dir = Path(__file__).resolve().parents[2] / 'datasources'
    monkeypatch.setattr(sources, 'HOME_DIR', str(resource_dir))
    tree = ET.parse(str(resource_dir / 'standard.xml'))
    config = next(node for node in tree.getroot() if node.get('name') == 'Observed')
    # Keep the real XML/CSV initialization and availability call chain; isolate SPC.
    config.remove(next(node for node in config if node.get('name') == 'SHARP'))
    source = sources.DataSource(config)
    available = sources.available
    for name, value in [('spc_time', None), ('spc_text', ''),
                        ('sharp_time', None), ('sharp_text', '')]:
        monkeypatch.setattr(available, name, value)
    monkeypatch.setattr(sources, 'loadDataSources', lambda: {'Observed': source})
    monkeypatch.setattr(sources, 'urlopen', lambda *a, **kw: Response())
    # Render separately from this constructor/data-initialization regression.
    monkeypatch.setattr(gui.Picker, '_Picker__initUI', lambda picker: None)
    return gui, sources, source


@pytest.mark.parametrize('error', [IncompleteRead(b'partial'), socket.timeout('slow server'),
                                 ConnectionResetError('connection reset')])
def test_picker_survives_incomplete_or_failed_response(observed, monkeypatch, error):
    gui, sources, source = observed
    responses = []

    def urlopen(*args, **kwargs):
        response = Response(error=error)
        responses.append(response)
        return response

    monkeypatch.setattr(sources.available, 'urlopen', urlopen)
    picker = gui.Picker(None)
    try:
        assert picker.all_times
        assert picker.run.hour in (0, 12)
        assert source._outlets['SPC']._is_available is False
        assert sources.available.spc_time is None
        assert sources.available.spc_text == ''
        assert all(response.closed for response in responses)
    finally:
        picker.close()


def test_picker_survives_empty_availability(observed, monkeypatch):
    gui, sources, source = observed
    monkeypatch.setattr(sources.available, 'urlopen', lambda *a, **kw: Response())
    picker = gui.Picker(None)
    try:
        assert picker.all_times
        assert picker.run.hour in (0, 12)
        assert source._outlets['SPC']._is_available is False
    finally:
        picker.close()


@pytest.mark.parametrize('body, expected', [
    (b'26111500_OBS 26111512_OBS', datetime(2026, 11, 15, 12)),
    (b'26111501_OBS 26111513_OBS', datetime(2026, 11, 15, 13)),
])
def test_picker_selects_latest_available_run(observed, monkeypatch, body, expected):
    gui, sources, source = observed
    response = Response(body)
    monkeypatch.setattr(sources.available, 'urlopen', lambda *a, **kw: response)
    picker = gui.Picker(None)
    try:
        assert picker.run == expected
        assert source._outlets['SPC']._is_available is True
        assert response.closed
    finally:
        picker.close()


@pytest.mark.parametrize('download', ['_download_spc', '_download_sharp'])
def test_initial_observed_requests_have_a_bounded_timeout(observed, monkeypatch, download):
    gui, sources, source = observed
    calls = []
    response = Response(b'complete response')

    def urlopen(*args, **kwargs):
        calls.append(kwargs)
        return response

    monkeypatch.setattr(sources.available, 'urlopen', urlopen)
    assert getattr(sources.available, download)() == 'complete response'
    assert 0 < calls[0].get('timeout', 0) <= 10
    assert response.closed


@pytest.mark.parametrize('error', [IncompleteRead(b'partial'), socket.timeout('slow server'),
                                 ConnectionResetError('connection reset')])
def test_station_availability_survives_network_read_errors(observed, monkeypatch, error):
    gui, sources, source = observed
    monkeypatch.setattr(sources.available, 'urlopen',
                        lambda *a, **kw: Response(error=error))
    outlet = source._outlets['SPC']
    assert outlet.getAvailableAtTime(dt=datetime(2026, 11, 15, 0)) == []
    assert outlet._is_available is False


@pytest.mark.parametrize('error', [IncompleteRead(b'partial'), socket.timeout('slow server'),
                                 ConnectionResetError('connection reset')])
def test_connection_probe_survives_network_errors(observed, monkeypatch, error):
    gui, sources, source = observed

    def urlopen(*args, **kwargs):
        raise error

    monkeypatch.setattr(sources, 'urlopen', urlopen)
    assert sources._pingURL('https://example.invalid/') is False
