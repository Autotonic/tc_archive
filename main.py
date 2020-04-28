import json
import re
import subprocess
import sys
import time
from datetime import datetime

import requests

global RELEVANT
RELEVANT = {}

def gettime():
    timefmt = datetime.utcnow().strftime('[%H:%M:%S]')
    return timefmt


def logtofile(message):
    message = '{} {}'.format(gettime(), message)
    print(message, file=sys.stderr)
    with open('tc.log', 'a') as f:
        f.write(message+"\n")

# EXTERNAL CALLS
def commit(version):
    version = f'2.0.0-{version}'
    logtofile(f'Commit for version: {version}')
    subprocess.run(['git', 'commit', '-a', '-m', version])

def gitpush():
    logtofile(f'Pushing to repository')
    subprocess.run(['git', 'push'])
    logtofile(f'Push complete')

def prettify(name):
    logtofile(f'Beautifying {name}')
    subprocess.run(['js-beautify', '--html', '--replace', name])
# END EXTERNAL CALLS

def clean(page):
    """Attempt to remove not-so-static content
    like csrf-token and tc-token
    """
    logtofile('Cleaning index.html')
    csrf = re.findall('csrf-token" content="(.+)"', page)
    tctoken = re.findall('tc-token="(.+)"', page)
    page = page.replace(csrf[0], 'TOKEN')
    page = page.replace(tctoken[0], 'TOKEN')
    return page


def gen_url_dict(version):
    baseurl = 'https://tinychat.com/webrtc/'
    css_client_main = baseurl + f'2.0.0-{version}/styles/client-main.css'
    css_client_nav = baseurl + f'2.0.0-{version}/styles/client-nav.css'
    html_index = baseurl + f'2.0.0-{version}/index.html'
    html_webrtc_app = baseurl + f'2.0.0-{version}/src/tinychat-webrtc-app/tinychat-webrtc-app.html'
    urls = {
        'css_main': css_client_main,
        'css_nav': css_client_nav,
        'index': html_index,
        'app': html_webrtc_app,
    }
    return urls



class Grab:
    def __init__(self, relevant):
        self.relevant = relevant
        self.latest = self.get_latest()

    def get_latest(self):
        r = requests.get('https://tinychat.com/room/abc')
        logtofile('Request for latest made: {}'.format(r))
        match = re.search('webrtc\/([0-9.-]+)\/', r.text)
        version = match[1].split('-')[1]
        return int(version)

    def get_relevant(self, start=24, sleep=6):
        logtofile(f'Getting relevant paths from {start} to {self.latest}')
        # look ahead
        for each in range(start, self.latest + 6):
            time.sleep(sleep)
            url = f'https://tinychat.com/webrtc/2.0.0-{each:02}/src/tinychat-webrtc-app/tinychat-webrtc-app.html'
            logtofile(f'Making request to {url}')
            r = requests.get(url)
            if r.status_code != 200:
                logtofile('FAIL ' + url)
            else:
                logtofile('WIN ' + url)
                self.relevant[int(each)] = gen_url_dict(int(each))
                self.get_files(int(each))
        # probably shouldn't be here
        with open('urls.json', 'w') as f:
            f.write(json.dumps(self.relevant, indent=4))

    def get_files(self, version):
        for url in self.relevant[version]:
            time.sleep(4)
            current = self.relevant[version][url]
            name = current.split('/')[-1]
            r = requests.get(current)
            logtofile(f'Request for {url} : {r}')
            with open(name, 'w') as f:
                if name == 'index.html':
                    new = clean(r.text)
                else:
                    new = r.text
                f.write(new)
            prettify(name)
        commit(version)

    def updatestatus(self):
        tmpl = 'current version: {}\nunreleased: {}'
        with open('readme.txt', 'w') as f:
            f.write(tmpl.format(get_latest(), max(self.relevant)))


    def run(self, exists):
        if exists is False:
            self.get_relevant()
            logtofile('Relevant paths obtained, rerunning')
            run(True)
        else:
            logtofile('JSON for paths exists, starting where we left off')
            if len(self.relevant) == 0:
                start = 24
            else:
                start = int(max(self.relevant))
            self.get_relevant(start=start)
            self.updatestatus()
            gitpush()


def main():
    client = Grab(relevant={})
    exists = False
    with open('urls.json', 'r') as f:
        j = f.read()
        if len(j) > 0:
            client.relevant = json.load(f)
            exists = True
    if len(client.relevant) == client.latest:
        logtofile("No update, exiting")
        sys.exit()

    else:
        client.run(exists)

main()
