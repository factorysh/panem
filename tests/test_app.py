import os
import pytest
import webtest
import responses

from panem.app import app as wsgi_app
from panem.app import db

API_KEY = 'toomanysecrets'


@pytest.yield_fixture
def app(request):
    db.drop_all()
    db.create_all()
    wsgi_app.debug = True
    return webtest.TestApp(
        wsgi_app,
        extra_environ={"HTTP_X_API_KEY": API_KEY})


def test_bad_auth():
    app = webtest.TestApp(wsgi_app)
    resp = app.get('/projects/', status='*')
    assert resp.status_int == 401

    resp = app.get('/')
    assert resp.status_int == 200
    resp.mustcontain('swaggerui')
    resp = app.get('/swagger.json')
    assert resp.status_int == 200

    app = webtest.TestApp(
        wsgi_app,
        extra_environ={"HTTP_X_API_KEY": "yo"})
    resp = app.get('/projects/', status='*')
    assert resp.status_int == 401


def test_app(app):
    resp = app.get('/')
    assert resp.status_int == 200
    resp.mustcontain('swaggerui')

    resp = app.get('/projects/')
    assert resp.status_int == 200
    assert isinstance(resp.json, list)

    resp = app.get('/projects/project_404/', status=404)
    assert resp.status_int == 404


def test_bad_data(app):
    resp = app.post('/projects/', {}, status=400)
    assert resp.status_int == 400

    resp = app.post_json('/projects/', {'environment': []}, status=400)
    assert resp.status_int == 400


@responses.activate
def test_project(app):

    for e in ['project/deploy', 'project/command']:
        url = os.environ['WEBHOOK_URL']
        responses.add(responses.POST, url,
                      json={'status': 'done'}, status=200)

    resp = app.post_json('/projects/', {
        'name': 'proj',
        'environment': [{'key': 'MY_KEY', 'value': 'value'}]
    })
    assert resp.status_int == 201
    data = resp.json
    assert data['name'] == 'proj'
    assert data['environment'] == [{'key': 'MY_KEY', 'value': 'value'}]

    resp = app.post_json('/projects/', {'name': 'proj'}, status=403)
    assert resp.status_int == 403

    resp = app.get('/projects/proj/')
    assert resp.status_int == 200
    data = resp.json
    assert data['name'] == 'proj'
    assert data['environment'] == [{'key': 'MY_KEY', 'value': 'value'}]

    resp = app.put_json('/projects/proj/', {
        'name': 'proj',
        'environment': [{'key': 'MY_KEY', 'value': 'new value'}]
    })
    assert resp.status_int == 201
    data = resp.json
    assert data['name'] == 'proj'
    assert data['environment'] == [{'key': 'MY_KEY', 'value': 'new value'}]

    resp = app.post_json('/projects/proj/_start')
    assert resp.status_int == 200
    assert resp.json == {'callback': None}

    resp = app.post_json('/projects/proj/_stop')
    assert resp.status_int == 200
    assert resp.json == {'callback': None}

    resp = app.post_json('/projects/proj/_stop', {'callback': 'http://'})
    assert resp.status_int == 200
    assert resp.json == {'callback': 'http://'}

    resp = app.post_json('/projects/proj/_none', status=404)
    assert resp.status_int == 404
