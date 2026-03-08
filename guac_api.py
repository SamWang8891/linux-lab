"""Guacamole REST API helper."""
import requests


class GuacamoleAPI:
    def __init__(self, base_url, admin_user, admin_pass):
        self.base_url = base_url.rstrip('/')
        self.admin_user = admin_user
        self.admin_pass = admin_pass
        self._token = None
        self._datasource = 'postgresql'  # or 'mysql', 'default'

    def _get_token(self):
        r = requests.post(f'{self.base_url}/api/tokens', data={
            'username': self.admin_user,
            'password': self.admin_pass,
        })
        r.raise_for_status()
        data = r.json()
        self._token = data['authToken']
        if data.get('dataSource'):
            self._datasource = data['dataSource']
        return self._token

    @property
    def token(self):
        if not self._token:
            self._get_token()
        return self._token

    def _api(self, method, path, **kwargs):
        url = f'{self.base_url}/api/session/data/{self._datasource}{path}'
        params = kwargs.pop('params', {})
        params['token'] = self.token
        try:
            r = requests.request(method, url, params=params, **kwargs)
            if r.status_code == 403:
                # Token expired, retry
                self._get_token()
                params['token'] = self.token
                r = requests.request(method, url, params=params, **kwargs)
            if not r.ok:
                detail = r.text[:500] if r.text else ''
                raise RuntimeError(f'Guacamole API {method} {path} → {r.status_code}: {detail}')
            return r.json() if r.text else None
        except RuntimeError:
            raise
        except Exception:
            raise

    def create_user(self, username, password):
        # Delete existing user first (ignore errors)
        try:
            self.delete_user(username)
        except Exception:
            pass
        return self._api('POST', '/users', json={
            'username': username,
            'password': password,
            'attributes': {
                'disabled': '',
                'expired': '',
                'access-window-start': '',
                'access-window-end': '',
                'valid-from': '',
                'valid-until': '',
                'timezone': 'Asia/Taipei',
            }
        })

    def delete_user(self, username):
        return self._api('DELETE', f'/users/{username}')

    def create_connection(self, name, protocol, hostname, port,
                          username=None, password=None, extra_params=None):
        params = {
            'hostname': hostname,
            'port': str(port),
            'security': 'any',
            'ignore-cert': 'true',
        }
        if username:
            params['username'] = username
        if password:
            params['password'] = password
        if extra_params:
            params.update(extra_params)

        data = self._api('POST', '/connections', json={
            'name': name,
            'protocol': protocol,
            'parameters': params,
            'attributes': {},
        })
        return data.get('identifier') if data else None

    def delete_connection(self, conn_id):
        return self._api('DELETE', f'/connections/{conn_id}')

    def grant_connection(self, username, conn_id):
        return self._api('PATCH', f'/users/{username}/permissions', json=[
            {
                'op': 'add',
                'path': f'/connectionPermissions/{conn_id}',
                'value': 'READ',
            }
        ])

    def list_connections(self):
        """Return dict of all connections: {id: {name, protocol, ...}}."""
        return self._api('GET', '/connections')

    def delete_connections_by_name(self, name_prefix):
        """Delete all connections whose name starts with name_prefix."""
        try:
            conns = self.list_connections()
            for conn_id, conn in conns.items():
                if conn.get('name', '').startswith(name_prefix):
                    try:
                        self.delete_connection(conn_id)
                    except Exception:
                        pass
        except Exception:
            pass

    def change_password(self, username, old_password, new_password):
        return self._api('PUT', f'/users/{username}/password', json={
            'oldPassword': old_password,
            'newPassword': new_password,
        })
