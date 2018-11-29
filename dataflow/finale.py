import csv
import apache_beam as beam


def temp_dict(line, weathdict):
    """Merger for Flights and Weather Datasets


    :param line: row received from the pipeline.
    :param weathdict: dictionary of the weather dataset
    :return: new line with the temperature at the last field and without the field key.
    """
    field_key = line[0]
    line_without_key = line[1:]
    temperature = weathdict.get(field_key, 9999)
    yield (line_without_key, temperature)


def hour_(full_time):
    """Extract the hour component from the full_time entry,
    which is in the format hourminutes.

    :param full_time:
    :return:hour
    """
    full_time = str(full_time)
    if len(full_time) <= 2:
        return full_time
    hour_only = full_time[:-2]
    return hour_only


def delaymarker(delay):
    """Takes the difference between
    the actual take off and the estimated time
    and return a label with the lateness status

    :param delay: string number of the delay of the flight
    :return: (string) No --> no delay, Yes -> delay
    """
    tradeoff_for_lateness = 15
    try:
        delay = float(delay)
    except:
        return 'No'
    if delay > tradeoff_for_lateness:
        return 'Yes'
    else:
        return 'No'


def georefe(lat, lon):
    """The function takes in input the (string) for latitude and longitude
    and return the equivalent geohash string.

    :param lat: latitude
    :param lon: longitude
    :return: geohash
    """
    import pygeohash as gh
    try:
        geoh = gh.encode(float(lat), float(lon))
    except:
        return "None"
    return geoh


if __name__ == '__main__':
    with beam.Pipeline('DirectRunner') as pipeline:
        ###############################################################################
        # Creating a Dictionary key -> Airport+date+hour, value --> max (temperature) #
        ###############################################################################
        weather = (pipeline
                   | 'Weather:Read File' >> beam.io.ReadFromText('weather.csv')
                   | 'Weather:lines Extract' >> beam.Map(lambda line: next(csv.reader([line])))
                   | 'Weather:Mapping' >> beam.Map(lambda fields: (
                       (str(fields[1])+'-'+str(fields[0]) + '-'+str(hour_(fields[2]))),
                       fields[3]))
                   | 'Weather:Reducing Temperature' >> beam.CombinePerKey(max)
                   )
        #########################################
        # Writing to file system the dictionary #
        #########################################
        weather \
            | 'Weather:Cleaning Output' >> beam.Map(lambda counter: '%s, %s' % (counter[0], counter[1])) \
            | 'weather:Write weather_dictionary' >> beam.io.textio.WriteToText('weather_dictionary')

        #####################################
        # Starting Pipeline for the flights #
        #####################################
        flights = (pipeline
                   | 'Flights:Read File'  >> beam.io.ReadFromText('flights_large.csv')
                   | 'Flights:Removeduplicates' >> beam.RemoveDuplicates()
                   | 'Flights:Lines Extract' >> beam.Map(lambda line: next(csv.reader([line])))
                   | 'Flight:Remove Heads' >> beam.Filter(lambda row: row[0] != 'Date')
                   | 'Flights:Mapping' >> beam.Map(lambda fields: (
                    (str(fields[5]) + '-' + str(fields[0]) + '-' + str(hour_(fields[7]))),
                    fields[0],
                    fields[7],
                    fields[1],
                    fields[5],
                    georefe(fields[16], fields[15]),
                    str(fields[5]) + '-->' + str(fields[3]),
                    delaymarker(fields[8]),
                    fields[18].ljust(10, '0')))
                   | 'Flights:Merge with Weather' >> beam.FlatMap(temp_dict, beam.pvalue.AsDict(weather))
                   | 'Flights:Clean for Output' >> beam.Map(lambda (data, temp): '{},{}'.format(','.join(data), temp))
                   )

        flights | 'Flights:Write flights_full_details' >> beam.io.textio.WriteToText('flights_full_details')

        ####################
        #   Aggregations   #
        ####################

        # Max Temperature each Airlines was operating for each day
        flights \
            | 'Maxtemp:lines extract' >> beam.Map(lambda line: next(csv.reader([line]))) \
            | 'Maxtemp:filter valid data' >> beam.Filter(lambda row: row[8] != '9999')  \
            | 'Maxtemp:Mapping' >> beam.Map(lambda fields: ((fields[2], fields[0]),
                                                                   ((float(fields[8])-32)*5/9))) \
            | 'Maxtemp:Reducing for Temperature' >> beam.CombinePerKey(max) \
            | 'Maxtemp:Cleaning for output' >> beam.Map(lambda (item1, item2): '%s, %s, %1.1f' % (item1[0], item1[1], item2)) \
            | 'Maxtemp:Write airlines_day_max_temperature' >> beam.io.textio.WriteToText('airlines_day_max_temperature')

        # Airlines Aggregate for number with or without delay
        flights \
            | 'Delay:Lines Extract' >> beam.Map(lambda line: next(csv.reader([line]))) \
            | 'Delay:Mapping' >> beam.Map(lambda fields: (fields[2], fields[6])) \
            | 'Delay:Combine' >> beam.combiners.Count.PerElement() \
            | 'Delay:Cleaning for output' >> beam.Map(lambda (item1, item2): '%s, %s %s' % (item1[0], item1[1], item2)) \
            | 'Delay:Write airlines_number_delay' >> beam.io.textio.WriteToText('airlines_number_delay')

        # Airline Total Number of Flights
        flights \
            | 'NumFlights:Lines Extract' >> beam.Map(lambda line: next(csv.reader([line]))) \
            | 'NumFlights:Mapping' >> beam.Map(lambda fields: fields[2]) \
            | 'NumFlights:Combine' >> beam.combiners.Count.PerElement() \
            | 'NumFlights:Cleaning for output' >> beam.Map(lambda counter: '%s, %s' % (counter[0], counter[1])) \
            | 'NumFlights:Write airlines_number_flights' >> beam.io.textio.WriteToText('airlines_number_flights')

        # Airline Total Number of Flights per Day
        flights \
            | 'NumFlightsDay:Lines Extract' >> beam.Map(lambda line: next(csv.reader([line]))) \
            | 'NumFlightsDay:Mapping' >> beam.Map(lambda fields: (fields[2], fields[0])) \
            | 'NumFlightsDay:Combine_' >> beam.combiners.Count.PerElement() \
            | 'NumFlightsDay:Cleaning for output' >> beam.Map(lambda (item1, item2): '%s, %s %s' % (item1[0], item1[1], item2)) \
            | 'NumFlightsDay:Write airlines_number_flights_per_day' >> beam.io.textio.WriteToText('airlines_number_flights_per_day')
