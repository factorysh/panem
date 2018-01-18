import argparse
import requests
import pprint
import os


def main():
    actions = ['get', 'put', 'start', 'stop', 'restart']
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'command', default='get',
        choices=actions,
        help="Action: %s, Default: get" % ', '.join(actions))
    parser.add_argument('project', help="project name")
    parser.add_argument('--host', default='panem')
    parser.add_argument('-p', '--port', type=int, default=80)
    args = parser.parse_args()
    session = requests.Session()
    token = os.environ.get('PANEM_TOKEN')
    if not token and os.path.isfile('.env'):
        with open('.env') as fd:
            for line in fd:
                if line.startswith('PANEM_TOKEN'):
                    k, v = line.strip().split('=', 1)
                    os.environ[k] = v
                    break
    session.headers.update({
        'X-Api-Key': os.environ['PANEM_TOKEN'],
    })
    url = 'http://{0.host}:{0.port}/projects/{0.project}/'.format(args)
    meth = session.get
    resp = meth(url)
    payload = resp.json()
    print('{0}: {1}'.format(meth.__name__.upper(), url))
    print('Resp: {}'.format(resp))
    pprint.pprint(payload)

    payload.pop('callback', None)

    meth = None
    if args.command == 'put':
        meth = session.put
    if args.command in ('start', 'restart', 'stop'):
        meth = session.post
        url += '_' + args.command
        payload = {}
    if meth:
        print('\n--')
        print('{0}: {1}'.format(meth.__name__.upper(), url))
        pprint.pprint(payload)
        print('Resp: {}'.format(resp))
        resp = meth(url, json=payload)
        pprint.pprint(resp.json())


if __name__ == '__main__':
    main()
