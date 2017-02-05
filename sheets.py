#!/usr/bin/python

from __future__ import print_function
import httplib2
import os

import numpy
import datetime

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

#try:
#    import argparse
#    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
#except ImportError:
#    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/sheets.googleapis.com-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Planilla Maker'


def get_credentials():
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'sheets.googleapis.com-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def get_sheet(spreadsheetId):
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    discoveryUrl = 'https://sheets.googleapis.com/$discovery/rest?version=v4'
    service = discovery.build('sheets', 'v4', http=http, discoveryServiceUrl=discoveryUrl)
    return service.spreadsheets().values()

def serial_to_date ( serial ) :
    tstamp = datetime.datetime(1899, 12, 30)
    return tstamp + datetime.timedelta( days=int(serial) )

class ModelData :

  def __init__ ( self , spreadsheetId ) :

    columns = "ABCDEFGHIJKLMN"
    self.spreadsheetId = spreadsheetId
    self.sheet = get_sheet(spreadsheetId)

    values = self.get('Shifts')

    n = 0
    COVERAGE = numpy.zeros((len(values),1), dtype=numpy.int8)
    for row in values:
        shape = COVERAGE.shape
        if len(row) > shape[1] :
            extend = numpy.zeros((shape[0], len(row)-shape[1]), dtype=numpy.int8)
            COVERAGE = numpy.concatenate((COVERAGE,extend),1)
        row = [r or 0 for r in row]
        row = ([int(r) for r in row])
        COVERAGE[n,:len(row)] = row
        n += 1
    #
    self.turnos = [columns[i] for i in range(COVERAGE.shape[1])]
    self.slots = range(COVERAGE.shape[0])
    #
    self.COVERAGE = []
    for t in range(COVERAGE.shape[1]) :
        hourspan = [s for s in self.slots if COVERAGE[s,t]]
        minmax = ( min(hourspan) , max(hourspan) )
        span = ( minmax[0] , minmax[1] - minmax[0] + 1 )
        if span == ( 0 , 24 ) :
            hourspan = [s for s in self.slots if not COVERAGE[s,t]]
            minmax = ( min(hourspan) , max(hourspan) )
            span = ( minmax[1]+1 , 24 - ( minmax[1] - minmax[0] + 1 ) )
        self.COVERAGE.append( span )
    #
    NEXTCOV = numpy.zeros(COVERAGE.shape, dtype=numpy.int8)
    for t in range(COVERAGE.shape[1]) :
        span = self.COVERAGE[t]
        if span[0] + span[1] > 24 :
            nextday = [s for s in self.slots if s<span[1]]
            NEXTCOV[nextday,t] = COVERAGE[nextday,t]
    COVERAGE -= NEXTCOV
    #
    self.matrix = []
    for s in self.slots :
        self.matrix.append("%-4d" % s + "  ".join(map(str, COVERAGE[s,:])))
    #
    self.next = []
    for s in self.slots :
        self.next.append("%-4d" % s + "  ".join(map(str, NEXTCOV[s,:])))

    values = self.get('Input')
    #
    self.assigned = values[1][1]
    self.days , self.weekends , self.visperas = [] , [] , []
    start = values[0][1]
    self.weeks = values[2][1]
    #self.weekdays = dict([(w,list()) for w in range(self.weeks)])
    self.weekdays = [list() for w in range(self.weeks)]
    for n in range(7*self.weeks) :
        self.days.append( start + n )
        self.weekdays[n//7].append( start + n )
        tstamp = serial_to_date(start)+datetime.timedelta(days=n)
        if int(tstamp.strftime("%w")) not in range(1,6) :
            self.weekends.append( start + n )
            if n :
                self.visperas.append( start + n - 1 )
    #
    self.names = values[4][1:]
    self.horas = {}
    for k,v in zip(self.names,values[5][1:]) :
        if v :
            self.horas[k] = v
    #
    self.restricciones = dict([ (n,[]) for n in self.names])
    for row in values[6:] :
        for n in range(len(row[1:])) :
            if row[n+1]:
                if isinstance( row[n+1], int ) :
                    if row[n+1] not in self.days :
                        print("WARNING : restriction on %s for %s out of range"%(self.names[n],serial_to_date(row[n+1]).strftime("%F")))
                        continue
                    self.restricciones[self.names[n]].append( row[n+1] )
                elif isinstance( row[n+1], str ) or isinstance( row[n+1], unicode ) :
                  if row[n+1].lower() in ( 'mon' , 'tue' , 'wed' , 'thu' , 'fri' , 'sat' , 'sun' ) :
                    for day in self.days :
                        if row[n+1].lower() == serial_to_date(day).strftime("%a").lower() :
                            self.restricciones[self.names[n]].append( day )
                else :
                    print("unparsed", self.names[n], row[n+1])

  def get ( self , rangeName ) :
    result = self.sheet.get(spreadsheetId=self.spreadsheetId, range=rangeName, valueRenderOption='UNFORMATTED_VALUE').execute()
    return result.get('values', [])

  def put ( self , rangeName , values ) :
    return self.sheet.update(spreadsheetId=self.spreadsheetId, range=rangeName,
                             body={'values': values}, valueInputOption='RAW').execute()

def main():

    spreadsheetId = '1H3jCVPEwQUb_RTKbOGTgQoAL8tKU1tyMhDUV2HPZtfw'
    model_data = ModelData(spreadsheetId)

    values = { 'dias': " ".join([str(d) for d in model_data.days]),
               'weeks': " ".join([str(d) for d in range(model_data.weeks)]),
               'weekdays': "\n".join([" ".join(map(str, model_data.weekdays[w])) for w in range(model_data.weeks)]),
               'weekends': "  ".join([ "%s 1" % day for day in model_data.weekends]),
               'visperas': "  ".join([ "%s 1" % day for day in model_data.visperas]),

               'turnos': " ".join(map(str, model_data.turnos)),
               'slots': " ".join(map(str, model_data.slots)),
               'matrix': "\n".join(model_data.matrix),
               'next': "\n".join(model_data.next),
               'personas': " ".join(model_data.names),
               'horas': "  ".join(["%s %s" % (k,v) for k,v in model_data.horas.iteritems() if v])
               }

    for k in values :
        print("%s -> %s"%(k, values[k]))

if __name__ == '__main__':
    main()

