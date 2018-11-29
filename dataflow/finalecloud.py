import csv
import apache_beam as beam


def temp_dict(line, weathdict):
    """

    :param line: row received from the pipeline.
    :param weathdict: dictionary of the
    :return: new line with the temperature at the last field and without the field key
    """
    field_key = line[0]
    line_without_key = line[1:]
    temperature = weathdict.get(field_key, 9999)
    yield (line_without_key, temperature)


def hour_(full_time):
    """Extract the hour component from the full_time entry
    hourminutes

    :param full_time:
    :return:hour
    """
    full_time = str(full_time)
    if len(full_time) <= 2:
        return full_time
    hour_only = full_time[:-2]
    return hour_only


def delaymarker(delay):
    """

    :param delay: string number of the delay of the flight
    :return: (string) no --> no delay, yes -> delay
    """
    try:
        delay = float(delay)
    except:
        return 'no'
    if delay > 15:
        return 'yes'
    else:
        return 'no'


def georefe(lat, lon):
    """The function takes in input the (string) for latitude and longitude
    and return the equivalent geohash string.

    :param lat: latitude
    :param lon: longitude
    :return: geohash
    """
    import pygeohash as gh
    try:
        mio = gh.encode(float(lat), float(lon))
    except:
        return "None"
    return mio


if __name__ == '__main__':
    with beam.Pipeline('DirectRunner') as pipeline:
        ###############################################################################
        # Creating a Dictionary key -> Airport+date+hour, value --> max (temperature) #
        ###############################################################################
        weather = (pipeline
                   | 'weather:read' >> beam.io.ReadFromText('weather.csv')
                   | 'weather:lines' >> beam.Map(lambda line: next(csv.reader([line])))
                   | 'weather:fields' >> beam.Map(lambda fields: (
                       (str(fields[1])+'-'+str(fields[0]) + '-'+str(hour_(fields[2]))),
                       fields[3]))
                   | 'weather:reducing for max temperature' >> beam.CombinePerKey(max)
                   )
        #########################################
        # Writing to file system the dictionary #
        #########################################
        weather \
            | "weather:cleaning" >> beam.Map(lambda counter: '%s, %s' % (counter[0], counter[1])) \
            | 'weather:write' >> beam.io.textio.WriteToText('weather_dictionary')

        #####################################
        # Starting Pipeline for the flights #
        #####################################
        flights = (pipeline
                   | 'flights:read'  >> beam.io.ReadFromText('flights_large.csv')
                   | 'flights:removeduplicates' >> beam.RemoveDuplicates()
                   | 'flights:lines' >> beam.Map(lambda line: next(csv.reader([line])))
                   | 'flight:remove heads' >> beam.Filter(lambda row: row[0] != 'Date')
                   | 'flights:fields' >> beam.Map(lambda fields: (
                    (str(fields[5]) + '-' + str(fields[0]) + '-' + str(hour_(fields[7]))),
                    fields[0],
                    fields[7],
                    fields[1],
                    fields[5],
                    georefe(fields[16], fields[15]),
                    str(fields[5]) + '-->' + str(fields[3]),
                    delaymarker(fields[8]),
                    fields[18].ljust(10, '0')))
                   | 'flights:addint temperature' >> beam.FlatMap(temp_dict, beam.pvalue.AsDict(weather))
                   | 'flights:compact' >> beam.Map(lambda (data, temp): '{},{}'.format(','.join(data), temp))
                   )

        flights | 'flights:write' >> beam.io.textio.WriteToText('flights_full_details')

        ########################
        ### Aggregations       #
        ########################


        flights \
        | 'maxtemp:lines2' >> beam.Map(lambda line: next(csv.reader([line]))) \
        | 'maxtemp:filtervalid data' >> beam.Filter(lambda row: row[8] != '9999')  \
        | 'maxtemp:filterairlines' >> beam.Map(lambda fields: ((fields[2], fields[0]), \
                                                               ((float(fields[8])-32)*5/9))) \
        | 'maxtemp:reducing for max temperature' >> beam.CombinePerKey(max) \
        | "maxtemp:combine2" >> beam.Map(lambda (item1, item2): '%s, %s, %1.1f' % (item1[0], item1[1], item2)) \
        | 'maxtemp:write_airlines' >> beam.io.textio.WriteToText('airlines_day_max_temperature')

        # Airlines Aggregate for number with or without delay

        flights \
        | 'delay:lines2' >> beam.Map(lambda line: next(csv.reader([line]))) \
        | 'delay:filterairlines' >> beam.Map(lambda fields: (fields[2], fields[6])) \
        | "delay:combine" >> beam.combiners.Count.PerElement() \
        | "delay:combine2" >> beam.Map(lambda (item1, item2): '%s, %s %s' % (item1[0], item1[1], item2)) \
        | 'delay:write_airlines' >> beam.io.textio.WriteToText('airlines_number_delay')

        # Airline Total Number of Flights

        flights \
        | 'flights:lines2' >> beam.Map(lambda line: next(csv.reader([line]))) \
        | 'airport:filterairlines' >> beam.Map(lambda fields: fields[2]) \
        | "flight:combine" >> beam.combiners.Count.PerElement() \
        | "flight:combine2" >> beam.Map(lambda counter: '%s, %s' % (counter[0], counter[1])) \
        | 'flight:write_airlines' >> beam.io.textio.WriteToText('airlines_number_flights')

        # Airline Total Number of Flights per Day
        flights \
        | 'flights:lines3' >> beam.Map(lambda line: next(csv.reader([line]))) \
        | 'airport:filterairlines2' >> beam.Map(lambda fields: (fields[2], fields[0])) \
        | "flight:combine_" >> beam.combiners.Count.PerElement() \
        | "flight:combine2_" >> beam.Map(lambda (item1, item2): '%s, %s %s' % (item1[0], item1[1], item2)) \
        | "flight:finale" >> beam.io.textio.WriteToText('airlines_number_flights_per_day')


