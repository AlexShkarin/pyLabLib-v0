'''
The MIT License (MIT)

Copyright (c) 2014 Andrew Rodgers

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

from __future__ import print_function

import requests
import time
from collections import defaultdict
from collections import Mapping, Set, Sequence


class UbntConfig(object):

    def __init__(self, config):
        object.__init__(self)
        self.config = self.parse_config(config)
        self.string_types = (str, unicode) if str is bytes else (str, bytes)
        self.iteritems = lambda mapping: getattr(
            mapping, 'iteritems', mapping.items)()

    def parse_line(self, line_string, data):
        Tree = lambda: defaultdict(Tree)
        path, val = line_string.split('=')
        fields = path.split('.')
        prop = fields.pop()
        obj = data
        for f in fields:
            if f.isdigit():
                items = obj.setdefault('items', [])
                idx = int(f) - 1
                while len(items) < idx + 1:
                    items.append(Tree())
                obj = items[idx]
            else:
                obj = obj[f]

        obj[prop] = val
        return data

    def parse_config(self, conf):
        Tree = lambda: defaultdict(Tree)

        data = Tree()

        for line in conf.splitlines():
            if not line:
                continue
            data = self.parse_line(line, data)

        return data

    def get_ntp(self):
        if self.config['ntpclient']['status'] == 'enabled':
            return self.config['ntpclient']['items'][0]
        else:
            return "ntpclient not enabled"

    def set_ntp(self, ntp_server):
        self.config['ntpclient']['status'] = 'enabled'
        self.config['ntpclient']['items'][0]['status'] = 'enabled'
        self.config['ntpclient']['items'][0]['server'] = ntp_server

    def get_crontab(self):
        if self.config['cron']['status'] == 'enabled':
            return self.config['cron']['items'][0]['job']['items']

    def add_cronjob(self, schedule, status, cmd, label):
        self.config['cron']['items'][0]['job']['items'].append(
            {'schedule': schedule, 'status': status, 'cmd': cmd,
                'label': label})
        return self.config['cron']['items'][0]['job']['items']

    def flatten_config(self, obj, path=(), memo=None):
        if memo is None:
            memo = set()
        iterator = None
        if isinstance(obj, Mapping):
            iterator = self.iteritems
        elif isinstance(obj, (Sequence, Set)) and not isinstance(
                obj, self.string_types):
            iterator = enumerate
        if iterator:
            if id(obj) not in memo:
                memo.add(id(obj))
                for path_component, value in iterator(obj):
                    if path_component == 'items':
                        for result in self.flatten_config(value, path, memo):
                            yield result
                    else:
                        try:
                            i = int(path_component)
                            path_component = str(i + 1)
                        except:
                            pass
                        for result in self.flatten_config(
                                value, path + (path_component,), memo):
                            yield result
                memo.remove(id(obj))
        else:
            yield path, obj

    def get_config_dump(self):
        flat = self.flatten_config(self.config)
        print(flat)
        lines = ['.'.join(path) + '=' + str(value) for path, value in flat]
        return '\n'.join(lines)

    def get_config(self):
        return self.config


class MfiDevice(object):
    """Base class for all mFi devices"""
    def __init__(self,  url, user, passwd, cache_timeout=2):

        """Provide a url to the mpower device, a username, and a password"""
        object.__init__(self)
        self.url = url
        self.user = user
        self.passwd = passwd
        self.cache_timeout = cache_timeout
        self.data_retrieved = 0
        self.session = requests.Session()
        #This get is necessary to set a cookie in the session prior to trying
        #to login might be better to stick it in the login method itself
        self.session.get(url)
        self.login()

    def login(self):
        post_data = {"uri": "/", "username": self.user,
                     "password": self.passwd}
        headers = {"Expect": ""}
        self.session.post((self.url + "/login.cgi"),
                          headers=headers, data=post_data,
                          allow_redirects=True)

    def get_data(self):
        if (time.time() - self.data_retrieved) > self.cache_timeout:
            r = self.session.get((self.url + "/mfi/sensors.cgi"))
            self.data_retrieved = time.time()
            self.data = r.json()
        return self.data

    def get_sensor(self, port_no):
        self.get_data()
        try:
            return self.data["sensors"][port_no - 1]
        except(KeyError, IndexError):
            print("Port #" + str(port_no) + " does not exist on this device")
            raise

    def get_param(self, port_no, param):
        try:
            sensor = self.get_sensor(port_no)
            return sensor[param]
        except(KeyError, IndexError):
            print("Port #" + str(port_no) + " does not have parameter: "
                  + param)

    def get_cfg(self):
        r = self.session.get(self.url + "/cfg.cgi")
        self.config = UbntConfig(r.text)
        return self.config

    def set_cfg(self, config_string):
        files = {'file': ('config.cfg', config_string)}
        p = self.session.post((self.url + "/system.cgi"), files=files)
        return p.text


class MPower(MfiDevice):
    """Provides an interface to a single mPower Device"""

    def get_power(self, port_no):
        return self.get_param(port_no, 'power')

    def switch(self, port_no, state="toggle"):
        if state == "toggle":
            current_state = self.get_param(port_no, 'output')
            next_state = not current_state
        else:
            if int(state) == 0 or int(state) == 1:
                next_state = int(state)
        data = {"output": str(next_state)}
        self.session.put((self.url + "/sensors/" + str(port_no) + "/"),
                         data=data)


class MPort(MfiDevice):
    """Provides an API to a single mPort Device"""

    def get_temperature(self, port_no, temp_format='c'):
        try:
            sensor = self.get_sensor(port_no)
            if "model" in sensor and sensor['model'] == 'Ubiquiti mFi-THS':
                if temp_format == "c":
                    return sensor['analog'] * 30 - 10
                elif temp_format == "f":
                    return (sensor['analog'] * 30 - 10) * 1.8 + 32
            else:
                raise IndexError
        except(IndexError):
            print("Sorry port #" + str(port_no) +
                  " either does not exist or is not a Temperature Sensor")