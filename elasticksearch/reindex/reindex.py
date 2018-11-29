from datetime import date, timedelta
from elasticsearch import Elasticsearch

SERVER = "10.10.10.10"
dest_index="enxzo"

es = Elasticsearch([{'host': SERVER, 'port': 9200}])

today = date.today()
yesterday= today - timedelta(days=1)

index_destination = "{}-{}".format(dest_index, today.strftime("%Y.%m.%d"))
print("index dest: {}".format(index_destination))

# reindex for the today index....
index_source = "logstash-{}*".format(today.strftime("%Y.%m.%d"))
print("index source for Today: {}".format(index_source))

try:
    result = es.reindex({
        "conflicts": "proceed",
        "source": {
            "index": index_source,
            "query": {
                "match": {
                    "host": "xxxxxxxxxx"
                }
            }
        },
        "dest": {"index": index_destination,
                 "op_type": "create"}
    }, wait_for_completion=True, request_timeout=300)
    print(result)
except:
    print("#############################")
    print("issue on the TODAY Reindex")


# reindex for the update yesterday index....
#Created just in case some thing was not working properly in the last 24 hours...
index_source = "logstash-{}*".format(yesterday.strftime("%Y.%m.%d"))
print("index source for Yesterday: {}".format(index_source))
try:
    result = es.reindex({
        "conflicts": "proceed",
        "source": {
          "index": index_source,
             "query": {
                "match": {
                   "host": "dogfood.osirium.net"
                    }
              }
        },
        "dest": {"index": index_destination,
                 "op_type": "create"}
    }, wait_for_completion=True, request_timeout=300)
    print(result)
except:
    print("#############################")
    print("issue on the Yesterday Reindex")

