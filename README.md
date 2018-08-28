# evtx2json
A tool to convert Windows evtx files (Windows Event Log Files) into JSON format and log to Splunk (optional) using HTTP Event Collector.

# installation
```
git clone https://github.com/vavarachen/evtx2json
pip install --user --requirement requirements.txt
```

# Help
```
$ python evtx2json.py -h
usage: evtx2json.py [--help] [--loglevel {0,10,20,30,40,50}]
                    [--disable_json_tweaks] [--splunk] [--host HOST]
                    [--token TOKEN] [--port PORT] [--proto {http,https}]
                    [--index INDEX] [--source SOURCE]
                    [--sourcetype SOURCETYPE] [--verify]
                    {process_files,process_folder} ...

Convert Windows evtx files to JSON

positional arguments:
  {process_files,process_folder}

optional arguments:
  --help, -h            This help message.
  --loglevel {0,10,20,30,40,50}, -v {0,10,20,30,40,50}
                        Log level
  --disable_json_tweaks
                        Skip customization to time, host, source etc. json
                        fields

Splunk Integration:
  Send JSON output to Splunk

  --splunk              Send JSON output to Splunk
  --host HOST           Splunk host with HEC listener
  --token TOKEN         HEC Token
  --port PORT           Splunk HEC listener port
  --proto {http,https}  Splunk HEC protocol
  --index INDEX         Splunk Index
  --source SOURCE       Event Source. NOTE: Computer name in evtx will
                        overwrite this value
  --sourcetype SOURCETYPE
                        Event Sourcetype
  --verify              SSL certificate verification

```

process_files module
```
$ python evtx2json.py process_files --help
usage: evtx2json.py process_files [-h] --files FILES [FILES ...]

optional arguments:
  -h, --help            show this help message and exit

Process evtx files:
  --files FILES [FILES ...], -f FILES [FILES ...]
                        evtx file
```

process_folder module
```
$ python evtx2json.py process_folder -h
usage: evtx2json.py process_folder [-h] --folder FOLDER

optional arguments:
  -h, --help       show this help message and exit

Process folder containing evtx files:
  --folder FOLDER  Folder containing evtx files
```


# Usage
Process evtx file(s)
```
python evtx2json.py process_files --files file1.evtx file2.evtx folder/*.evtx
```

Process multiple evtx files in a folder
```
python evtx2json.py process_folder --folder /path/to/evtx_folder
```

Enable logging to Splunk
```
python evtx2json.py --splunk --host splunkfw.domain.tld --port 8888 --token BEA33046C-6FEC-4DC0-AC66-4326E58B54C3 \
    process_files -f samples/*.evtx
```

Enable logging to Splunk but disable JSON modifications
```
python evtx2json.py --splunk --host splunkfw.domain.tld --port 8888 --token BEA33046C-6FEC-4DC0-AC66-4326E58B54C3 \
    --disable_json_tweaks process_files -f samples/*.evtx
```

![Splunk Output Example](https://github.com/vavarachen/evtx2json/blob/master/resources/example1.png)
