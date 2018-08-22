# evtx2json
A tool to convert Windows evtx (Event log export) files into JSON format and log to Splunk (optional) using HTTP Event Collector.

# installation
```
git clone https://github.com/vavarachen/evtx2json
```

# Usage
Process single file
```
python evtx2json file.evtx
```

Process multiple files
```
python evtx2json /path/to/evtx/files
```

![Splunk Output Example](https://github.com/vavarachen/evtx2json/blob/master/resources/example1.png)