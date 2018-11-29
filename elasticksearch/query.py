import pandas as pd
from datetime import datetime
from elasticsearch import Elasticsearch
import json


#################
#  Full Search  #
#################
# New Version.....
def search_UserFailedLoginOdc(from_day,to_day):
    es = Elasticsearch([{'host': '10.10.10.10', 'port': 9200}],
                       
                       scheme="http")

    Data = pd.DataFrame()
    log='logstash*'

    res = es.search(index=log, body={
          "size": 10000,
          "query": {
          "match": {
          "host": 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
           }}
                })

       #     print("Got %d Hits:" % res['hits']['total'])

    for hit in res['hits']['hits']:
        message= json.loads(hit['_source']['message'])
        if message['name']=='---------------------':
            ser = pd.Series()#data=Info)
            ser['@timestamp'] = '_source']['@timestamp']
            #ser['args']=message['args']   #### Added Message....
            ser['user']=message['args']['username']
            ser['device'] = message['args']['hostname']
            ser['client_address'] = message['args']['client_address']
            ser['device_address'] = message['args']['device_address']


            Data = Data.append(ser, ignore_index=True)

    return Data

Data=search_UserFailedLoginOdc(1,31)


