import os
import time

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_restplus import (Api, Resource, fields)

from sqlalchemy.dialects.postgresql import JSON

DB_URL = (
    'postgres+pg8000://{POSTGRES_USER}:{POSTGRES_PASSWORD}'
    '@postgres/{POSTGRES_DB}'
).format(**os.environ)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
db = SQLAlchemy(app)

app.config['SWAGGER_UI_DOC_EXPANSION'] = 'list'
app.config['SWAGGER_UI_JSONEDITOR'] = True
api = Api(app)


class InstanceModel(db.Model):

    slug = db.Column(db.String(80), primary_key=True)
    name = db.Column(db.String(80))
    env = db.Column(JSON)

    def to_dict(self):
        return dict(
            name=self.name,
            env=self.env)

    @classmethod
    def from_dict(cls, data):
        o = cls()
        for k, v in data.items():
            if k not in (id,):
                setattr(o, k, v)
        db.session.add(o)
        db.session.commit()
        return o


while True:
    try:
        db.create_all()
    except Exception:
        print('waiting for db...')
        time.sleep(2)
    else:
        break


env_key = api.model('EnvKey', {
    'key': fields.String,
    'value': fields.String,
})

instance = api.model('Instance', {
    'slug': fields.String,
    'name': fields.String,
    'compose': fields.String,
    'env': fields.List(fields.Nested(env_key)),
})


@api.route('/instances/', endpoint='instances')
@api.doc()
class Instances(Resource):

    @api.marshal_list_with(instance)
    def get(self):
        return [i.to_dict() for i in InstanceModel.query.all()]

    @api.marshal_with(instance)
    @api.expect(instance)
    def post(self, **kwargs):
        o = InstanceModel.from_dict(kwargs)
        return o.to_dict()


@api.route('/instances/<slug>', endpoint='instance')
@api.doc()
class Instance(Resource):

    @api.marshal_with(instance)
    def get(self, slug=None, **kwargs):
        return InstanceModel.query.filter_by(slug=slug).one().to_dict()

    @api.marshal_with(instance)
    @api.expect(instance)
    def post(self, slug=None, **kwargs):
        o = InstanceModel.query.filter_by(slug=slug).one()
        return o.to_dict()
