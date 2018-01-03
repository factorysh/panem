import os

import yaml
import requests
from passlib.hash import pbkdf2_sha256

from flask import Flask, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_restplus import (Api, Resource, fields)

from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm.exc import NoResultFound

from raven.contrib.flask import Sentry


with open(os.environ['PANEM_CONFIG']) as fd:
    PANEM_CONFIG = yaml.load(fd.read())


ALLOWED_PATHS = ('/swaggerui/', '/swagger.json')
API_KEY = os.environ['API_KEY']
WEBHOOK_URL = os.environ['WEBHOOK_URL']
WEBHOOK_API_KEY = os.environ['WEBHOOK_API_KEY']
DB_URL = (
    'postgres+pg8000://{POSTGRES_USER}:{POSTGRES_PASSWORD}'
    '@{POSTGRES_HOST}/{POSTGRES_DB}'
).format(**os.environ)

AUTHORIZATIONS = {
    'apikey': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'X-API-KEY'
    }
}

session = requests.Session()

app = Flask(__name__)
# See https://docs.sentry.io/clients/python/integrations/flask/
if os.getenv('SENTRY_DSN'):  # pragma: no cover
    from raven.transport.threaded_requests import ThreadedRequestsHTTPTransport
    app.config['SENTRY_CONFIG'] = {
        'transport': ThreadedRequestsHTTPTransport,
    }
    sentry = Sentry(app)

app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

app.config['SWAGGER_UI_DOC_EXPANSION'] = 'list'
app.config['SWAGGER_UI_JSONEDITOR'] = True
api = Api(app, authorizations=AUTHORIZATIONS, security='apikey')


def send_event(event, **payload):
    payload.update(event=event)
    data = dict(
        variables=payload,
        **PANEM_CONFIG.get('events', {}).get(event, {}))
    resp = session.post(WEBHOOK_URL,
                        json=data,
                        headers={'X-API-KEY': WEBHOOK_API_KEY})
    resp.raise_for_status()
    return resp


class ProjectModel(db.Model):

    name = db.Column(db.String(80), primary_key=True)
    environment = db.Column(JSON)

    def env_to_dict(self, env):
        return {i['key']: i['value'] for i in env}

    def to_dict(self):
        value = dict(
            name=self.name,
            environment=[{'key': k, 'value': v}
                         for k, v in self.environment.items()]
        )
        return value

    def from_dict(self, data):
        if 'environment' not in data:
            self.environment = {}
        for k, v in data.items():
            if k == 'environment':
                v = self.env_to_dict(v)
            setattr(self, k, v)
        db.session.add(self)
        db.session.commit()
        return self

    @classmethod
    def from_name(cls, name):
        try:
            return cls.query.filter_by(name=name).one()
        except NoResultFound:
            abort(404)


env_key = api.model('EnvKey', {
    'key': fields.String,
    'value': fields.String,
})

project = api.model('Project', {
    'name': fields.String(required=True),
    'environment': fields.List(fields.Nested(env_key), required=True),
})


@api.route('/projects/', endpoint='projects')
@api.doc()
class Projects(Resource):

    @api.marshal_list_with(project)
    def get(self):
        return [i.to_dict() for i in ProjectModel.query.all()]

    @api.expect(project)
    @api.marshal_with(project)
    def post(self, **kwargs):
        try:
            name = api.payload['name']
        except (TypeError, KeyError):
            abort(400, 'Invalid request')
        try:
            ProjectModel.query.filter_by(name=name).one()
        except NoResultFound:
            o = ProjectModel()
            o.from_dict(api.payload)
            payload = o.to_dict()
            p = [dict(name=o.name)]
            send_event('created', projects=p, environment=o.environment)
            return payload, 201
        else:
            abort(403)


@api.route('/projects/<name>/', endpoint='project')
@api.doc()
class Project(Resource):

    @api.marshal_with(project)
    def get(self, name=None, **kwargs):
        return ProjectModel.from_name(name).to_dict()

    @api.expect(project)
    @api.marshal_with(project)
    def put(self, name=None, **kwargs):
        o = ProjectModel.from_name(name)
        try:
            data = api.payload['environment']
        except (TypeError, KeyError):
            abort(400, 'Invalid request')
        o.from_dict({'environment': data})
        payload = o.to_dict()
        p = [dict(name=o.name)]
        send_event('updated', projects=p, environment=o.environment)
        return payload, 201


def post_action(resource, name=None, **kwargs):
    o = ProjectModel.from_name(name)
    action = request.path.strip('/').split('/')[-1].strip('_')
    resp = send_event(action, project=dict(name=o.name))
    return resp.json(), resp.status_code


@api.route('/projects/<name>/_start', endpoint='project_start')
@api.doc()
class Start(Resource):
    post = post_action


@api.route('/projects/<name>/_stop', endpoint='project_stop')
@api.doc()
class Stop(Resource):
    post = post_action


@api.route('/projects/<name>/_restart', endpoint='project_restart')
@api.doc()
class Restart(Resource):
    post = post_action


class Auth:

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        path = environ['PATH_INFO']
        if not (path == '/' or path.startswith(ALLOWED_PATHS)):
            valid = False
            key = environ.get('HTTP_X_API_KEY')
            if key:
                try:
                    valid = pbkdf2_sha256.verify(key, API_KEY)
                except ValueError:
                    pass
            if not valid:
                start_response("401 Unauthorized", [])
                return [b'']
        return self.app(environ, start_response)


app.wsgi_app = Auth(app.wsgi_app)


if not os.environ.get('TESTING'):
    db.create_all()


def main():
    app.run(host=os.getenv('LISTEN', '0.0.0.0'),
            port=int(os.getenv('PORT', 5000)))
