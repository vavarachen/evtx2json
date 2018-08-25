"""
Script to convert evtx_dump.py XML output (https://github.com/williballenthin/python-evtx)
to JSON and push to Splunk via HTTP Event Collector (pip install splunk-hec-handler)

evtx2json.py <folder with evtx files>
evtx2json.py <single evtx file>

"""
import os.path
import sys
import logging
from splunk_hec_handler import SplunkHecHandler
from xmljson import badgerfish as bf
import json
import xml.etree.ElementTree as ET
import Evtx.Evtx as evtx
import time
from glob import glob
import argparse

logger = logging.getLogger('evtx2json')
logger.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler()
stream_handler.level = logging.WARNING
logger.addHandler(stream_handler)

# If using self-signed certificate, set ssl_verify to False
# If using http, set proto to http
token = "EA33046C-6FEC-4DC0-AC66-4326E58B54C3"
splunk_handler = SplunkHecHandler('splunkfw.domain.tld',
                                 token, index='evtx2json',
                                 port=8888, proto='https', ssl_verify=True,
                                 source="evtx2json", sourcetype='_json')
logger.addHandler(splunk_handler)

# Additional fields for Splunk indexing
fields = dict({})

global event_counter, error_counter


def remove_namespace(tree):
    """
    Namespace can make Splunk output ugly.  This function removes namespace from all elements
    e.g element.tag = '{http://schemas.microsoft.com/win/2004/08/events/event}System'
    :param tree: xml ElementTree Element
    :return: xml ElementTree Element with namespace removed
    """
    # Remove namespace
    for element in tree.getiterator():
        try:
            if element.tag.startswith('{'):
                element.tag = element.tag.split('}')[1]
        except:
            pass

    return tree


def xml2json(xml_str):
    """
    Convert string xml (after striping namespace) output from evtx.Evtx to XML tree object
    :param xml_str: string
    :return: xml ElementTree Element
    """
    try:
        tree = remove_namespace(ET.fromstring(str(xml_str)))
        obj = bf.data(tree)
    except:
        logger.error("Failed to convert XML to JSON for %s" % xml_str)
    else:
        return obj


def iter_evtx2xml(evtx_file):
    """
    Generator function to read events from evtx file and convert to xml
    :param evtx_file: file path string
    :return: generator to xml string representation of evtx event
    """
    global error_counter, event_counter
    error_counter = 0
    event_counter = 0
    try:
        with evtx.Evtx(evtx_file) as log:
            # process each log entry and return xml representation
            for record in log.records():
                event_counter += 1
                try:
                    yield record.xml()
                except Exception as err:
                    error_counter += 1
                    logger.error("Failed to convert EVTX to XML for %s. Error count: %d" % (evtx_file, error_counter))
    except Exception as err:
        raise


def _transform_system(output):
    # xmljson output of System field is rather unruly Event{System{1{}...n{}}}
    # This function cleans up the System section for easier Splunking.
    try:
        systemdata = output['Event']['System']
        new_systemdata = {}
    except KeyError:
        logger.debug('Missing "System" section. Skipping.')
    else:
        for k,v in systemdata.items():
            if hasattr(v, 'items') and len(v) == 1 and '$' in v.keys():
                new_systemdata[k] = v['$']
            else:
                new_systemdata[k] = v

        _ = output['Event'].pop('System')
        output['Event']['System'] = {}
        output['Event']['System'].update(new_systemdata)
    finally:
        return output


def _transform_eventdata(output):
    # xmljson output of EventData field is rather unruly Event{EventData{ Data[1{}...n{}] }}
    # This function cleans up the EventData section for easier Splunking.
    try:
        eventdata = output['Event']['EventData']
    except:
        logger.debug('Missing "EventData" section. Skipping.')
    else:
        new_eventdata = {}
        for data in eventdata['Data']:
            if '@Name' in data.keys() and '$' in data.keys():
                new_eventdata[data['@Name']] = data['$']
            elif '@Name' in data.keys() and '$' not in data.keys():
                new_eventdata[data['@Name']] = None
            else:
                new_eventdata.extend(data)
        _ = output['Event'].pop('EventData')
        output['Event']['EventData'] = {}
        output['Event']['EventData'].update(new_eventdata)
    finally:
        return output


def splunkify(output, source=sys.argv[1], transform=True):
    """
    Any customization to the final splunk output goes here
    :param output: JSON obj returned by xml2json
    :param source: str. evtx source
    :return: JSON obj with Splunk customizations
    """

    if transform:
        event = _transform_system(output)
        event = _transform_eventdata(event)
    else:
        event = output

    # Custom fields for Splunk processing
    event['Event']['fields'] = {}

    # Set Splunk event _time to timestamp in the evtx event.
    try:
        _ts = event['Event']['System']['TimeCreated']['@SystemTime']
        try:
            _ts = time.mktime(time.strptime(_ts.strip(), "%Y-%m-%d %H:%M:%S.%f"))
        except ValueError:
            _ts = time.mktime(time.strptime(_ts.strip(), "%Y-%m-%d %H:%M:%S"))
    except KeyError:
        logger.warning("Event missing TimeCreated field")
        _ts = time.time()
    except ValueError:
        logger.warning("Failed to convert TimeCreated (%s) to epoch timestamp" % _ts)
        _ts = time.time()
    else:
        # example evtx timestamp '2016-07-01 11:05:48.162424'
        event['Event']['fields']['time'] = _ts

    # Set host field to Computer names in the evtx event
    try:
        if transform:
            _host = event['Event']['System']['Computer']
        else:
            _host = event['Event']['System']['Computer']['$']
    except KeyError:
        logger.warning("Event missing Computer field")
    else:
        event['Event']['fields']['host'] = _host

    # Set source field to name of the evtx file
    event['Event']['fields']['source'] = source

    return event


if __name__ == "__main__":
    if len(sys.argv) == 1 or len(sys.argv) > 2:
        print("Usage:\n\t%s /path/to/file.evtx \n\t %s /folder/containing/evtxfiles"
              % (sys.argv[0], sys.argv[0]))
        sys.exit(-1)

    start_time = int(time.time())
    if sys.argv[1].endswith(".evtx"):
        # argument is a single evtx file
        logger.debug("Now processing %s" % sys.argv[1])
        success_counter = 0
        for xml_str in iter_evtx2xml(sys.argv[1]):
            try:
                output = splunkify(xml2json(xml_str))
            except Exception:
                error_counter += 1
            else:
                logger.info(json.loads(json.dumps(output['Event'])))
                success_counter += 1

        delta_secs = (int(time.time()) - start_time)
        logger.info({'file': sys.argv[1], 'total_events': event_counter, 'pass': success_counter,
                        'fail': error_counter, 'time': start_time, 'elapsed_sec': delta_secs})
    else:
        # argument is a path to folder containing evtx files
        for evtx_file in glob(os.path.join(sys.argv[1], "*.evtx")):
            logger.debug("Now processing %s" % evtx_file)
            success_counter = 0
            for xml_str in iter_evtx2xml(evtx_file):
                try:
                    output = splunkify(xml2json(xml_str), evtx_file)
                    logger.info(json.loads(json.dumps(output['Event'])))
                except Exception:
                    # Update global error counter
                    error_counter += 1
                else:
                    success_counter += 1

                delta_secs = (int(time.time()) - start_time)
                logger.info({'file': sys.argv[1], 'total_events': event_counter, 'pass': success_counter,
                             'fail': error_counter, 'time': start_time, 'elapsed_sec': delta_secs})


