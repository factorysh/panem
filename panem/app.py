import os

import requests
from passlib.hash import pbkdf2_sha256

from flask import Flask, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_restplus import (Api, Resource, fields)

from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm.exc import NoResultFound

from raven.contrib.flask import Sentry


ALLOWED_PATHS = ('/swaggerui/', '/swagger.json')
API_KEY = os.environ['API_KEY']
WEBHOOK_URL = os.environ['WEBHOOK_URL']
WEBHOOK_API_KEY = os.environ['WEBHOOK_API_KEY']
DB_URL = (
    'postgres+pg8000://{POSTGRES_USER}:{POSTGRES_PASSWORD}'
    '@postgres/{POSTGRES_DB}'
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
if os.getenv('SENTRY_DSN'):
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


# TODO
# Use config for this part
# WIP
PLAYBOOKS = {
    'start': 'command.yml',
    'stop': 'command.yml',
    'restart': 'command.yml',
    'created': 'site.yml',
    'updated': 'site.yml',
}


def send_event(event, **payload):
    payload.update(event=event)
    pb = PLAYBOOKS[event]
    resp = session.post(WEBHOOK_URL,
                        json=dict(variables=payload, playbook=pb),
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
    'name': fields.String,
    'environment': fields.List(fields.Nested(env_key)),
})


@api.route('/projects/', endpoint='projects')
@api.doc()
class Projects(Resource):

    @api.marshal_list_with(project)
    def get(self):
        return [i.to_dict() for i in ProjectModel.query.all()]

    @api.marshal_with(project)
    @api.expect(project)
    def post(self, **kwargs):
        name = request.json['name']
        try:
            ProjectModel.query.filter_by(name=name).one()
        except NoResultFound:
            o = ProjectModel()
            o.from_dict(request.json)
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

    @api.marshal_with(project)
    @api.expect(project)
    def put(self, name=None, **kwargs):
        o = ProjectModel.from_name(name)
        o.from_dict({'environment': request.json['environment']})
        payload = o.to_dict()
        p = [dict(name=o.name)]
        send_event('updated', projects=p, environment=o.environment)
        return payload, 201


@api.route('/projects/<name>/_start', endpoint='project_start')
@api.route('/projects/<name>/_stop', endpoint='project_stop')
@api.route('/projects/<name>/_restart', endpoint='project_restart')
@api.doc()
class Action(Resource):

    def post(self, name=None, **kwargs):
        o = ProjectModel.from_name(name)
        action = request.path.strip('/').split('/')[-1].strip('_')
        if action not in ('start', 'stop', 'restart'):
            abort(404)
        resp = send_event(action, project=dict(name=o.name))
        return resp.json(), resp.status_code


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
            port=os.getenv('PORT', 5000))
