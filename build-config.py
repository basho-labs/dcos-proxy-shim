#! /usr/bin/env python

"""Build NGINX config for DCOS automatic load balancing."""

__author__ = 'David Parrish <david@dparrish.com>'
__author__ = 'Travis B. Hartwell <thartwell@contractor.basho.com>'

from jinja2 import Template
import json
import os
import requests
import subprocess
import sys
import time
import socket


TEMPLATE="""
server {
    listen 80 default_server;
    listen [::]:80 default_server ipv6only=on;

    root /usr/share/nginx/html;
    index index.html index.htm;

    # Make site accessible from http://localhost/
    server_name localhost;

    # We're running in a Docker container, so output logs to stderr and stdout
    error_log /proc/self/fd/2;
    access_log /proc/self/fd/1;

    location ^~ /service/ {
        {% for appId, hostPort in apps|dictsort %}
        location ~* /service{{ appId }} {
            rewrite /service{{ appId }}/(.*) /$1  break;
            proxy_pass http://{{ hostPort }};
        }
        {% endfor %}
    }

    location / {
        # First attempt to serve request as file, then
        # as directory, then fall back to displaying a 404.
        try_files $uri $uri/ =404;
        # Uncomment to enable naxsi on this location
        # include /etc/nginx/naxsi.rules
    }
}
"""

def main(argv):
    try:
        marathon_url = os.environ.get("MARATHON_URL", "http://leader.mesos:8080")
        old_config = None
        while True:
            params = {
                'apps': {},
            }

            s = requests.Session()
            apps = json.loads(s.get('%s/v2/apps' % marathon_url).text)
            for app in apps['apps']:
                tasks = json.loads(s.get('%s/v2/apps%s/tasks' % (marathon_url, app['id']),
                                         headers={'Accept': 'application/json'}).text)
                hostPort = None
                # Assume only one task
                task = tasks['tasks'][0]
                try:
                    ip = socket.gethostbyname(task['host'])
                except socket.gaierror:
                    print "Can't look up host %s" % task['host']
                else:
                    hostPort = "%s:%s" % (ip, task['ports'][0])

                if hostPort:
                    params['apps'][app['id']] = hostPort

            template = Template(TEMPLATE)
            new_config = template.render(params)

            if new_config != old_config:
                with file('/etc/nginx/sites-available/default', 'w') as fh:
                    fh.write(new_config)
                test = subprocess.Popen(['/usr/sbin/nginx', '-t'], stderr=subprocess.PIPE)
                output = test.communicate()
                if test.returncode != 0:
                    if old_config:
                        print 'Error generating new NGINX configuration, not reloading'
                        return
                    else:
                        raise RuntimeError('Error generating NGINX configuration')
                subprocess.call(['/usr/sbin/nginx', '-s', 'reload'])
                old_config = new_config
            time.sleep(10)
    except KeyboardInterrupt:
        return 1

if __name__ == '__main__':
    sys.exit(main(sys.argv))

