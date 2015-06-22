#!/usr/bin/python

import json, urllib2, re, sys, os, shutil
from optparse import OptionParser
from datetime import datetime

extfacts_dir_path = "/etc/facter/facts.d/"

usage = "usage: %prog [options] URL"
optionparser = OptionParser(usage=usage)
optionparser.add_option("-f", "--fact-name", dest="name", default=False,
        help="Fact's name for filename.\nWill be guessed from fact if not provided.", metavar="NAME")
optionparser.add_option("-t", "--file-type", dest="filetype", default=False,
    help="Fact's file type (currently only json is valid).\nWill be guessed from fact's URL if not provided.", metavar="FILETYPE")
optionparser.add_option("-d", "--debug", dest="debug", action="store_true", default=False,
        help="Enable debug")
(options, args) = optionparser.parse_args()
if len(args) != 1:
    optionparser.error("You need to provide one argument -- URL")
else:
    url = args[0]

if options.debug: print "[%s] [DEBUG] Downloading file from %s" % (str(datetime.now()), url)
file_stream = urllib2.urlopen(url).read().rstrip('\n')
if options.filetype == False:
    regexp = re.compile("^.*?\.([A-Za-z0-9]+)$")
    extension = regexp.match(url).group(1)
else:
   extension = options.filetype
if options.debug: print "[%s] [DEBUG] File's type is %s" % (str(datetime.now()), extension)

def check_and_store_json (stream):
    try:
        json_fact = json.loads(stream)
    except ValueError, e:
        print >> sys.stderr, """\
[%s] [ERROR] The file is not JSON! Look at it yourself:
-----------8<-----------
%s
-----------8<-----------""" % (str(datetime.now()), stream)
        sys.exit(1)
        return False
    filename = options.name + ".json" if options.name else json_fact.keys()[0] + ".json"
    if options.debug: print "[%s] [DEBUG] File name will be %s" % (str(datetime.now()), filename)
    saving_result = save_to_external_fact_file (json.dumps(json_fact,indent=1), filename)
    if saving_result: return True

def save_to_external_fact_file (content, filename):
    tmp_file_name = "/tmp/fact_" + filename + ".tmp"
    new_file_name = extfacts_dir_path + filename
    if options.debug: print "[%s] [DEBUG] Saving tmp file %s" % (str(datetime.now()), tmp_file_name)
    tmp_file = open(tmp_file_name,'w')
    tmp_file.write(content)
    tmp_file.close()
    if options.debug: print "[%s] [DEBUG] Moving %s to %s" % (str(datetime.now()), tmp_file_name, new_file_name)
    try: shutil.move(tmp_file_name, new_file_name)
    except (OSError, IOError), e:
        print >> sys.stderr, "[%s] [ERROR] Can't move %s to %s: %s" % (str(datetime.now()), tmp_file_name, new_file_name, e)
        sys.exit(1)
    return True

if extension == 'json':
    if (check_and_store_json(file_stream)):
        if options.debug: print "[%s] [DEBUG] Done" % (str(datetime.now()))
    else:
        print >> sys.stderr, "Couldn't save the file."
        sys.exit(1)
