#!/usr/bin/python

from __future__ import print_function

import json
from slugify import slugify

import httplib2
import argparse
import os

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage


planilla_args = argparse.ArgumentParser()
planilla_args.add_argument("calendar")

class GoogleApp :

    CLIENT_SECRET_FILE = 'client_secret.json'

    def __init__ ( self , application_name , scopes ) :
        self.application_name = application_name
        home_dir = os.path.expanduser('~')
        credential_dir = os.path.join(home_dir, '.credentials')
        if not os.path.exists(credential_dir):
            os.makedirs(credential_dir)
        credential_path = os.path.join(credential_dir, '%s.json'%slugify(application_name))
        store = Storage(credential_path)

        self.credentials = store.get()
        if not self.credentials or self.credentials.invalid:
            api_url = 'https://www.googleapis.com/auth/'
            scopes = " ".join([api_url+scope for scope in scopes])
            print(scopes)
            flow = client.flow_from_clientsecrets(self.CLIENT_SECRET_FILE, scopes)
            flow.user_agent = self.application_name
            print(planilla_args)
            print(tools.argparser)
            flags = argparse.ArgumentParser(parents=[planilla_args, tools.argparser]).parse_args()
            if flags:
                self.credentials = tools.run_flow(flow, store, flags)
            else: # Needed only for compatibility with Python 2.6
                self.credentials = tools.run(flow, store)

    def calendars ( self ) :
        http = self.credentials.authorize(httplib2.Http())
        service = discovery.build('calendar', 'v3', http=http)
    #    bichos = service.calendarList().list().execute()
    #    print(json.dumps( bichos , indent=4 ))
        return service.calendars()

    def events ( self ) :
        http = self.credentials.authorize(httplib2.Http())
        service = discovery.build('calendar', 'v3', http=http)
        return service.events()

    def get_sheet ( self , spreadsheetId ) :
        http = self.credentials.authorize(httplib2.Http())
        discoveryUrl = 'https://sheets.googleapis.com/$discovery/rest?version=v4'
        service = discovery.build('sheets', 'v4', http=http, discoveryServiceUrl=discoveryUrl)
        return service.spreadsheets().values()


def main():
    app = GoogleApp('Google APIs', ['calendar', 'spreadsheets'])
    print(app.credentials)


if __name__ == '__main__':
    main()

