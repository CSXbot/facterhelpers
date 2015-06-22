#!/local/python/bin/python

from Facter import Facter
import json, sys, socket
from optparse import OptionParser
from colorama import Fore, Back, Style
from pygments.lexers import JsonLexer
from pygments.formatters import TerminalFormatter
from pygments.styles import native
from operator import itemgetter

usage = "usage: %prog [-n]"
optionparser = OptionParser(usage=usage)

optionparser.add_option("-s", "--max-severity", dest="maxSeverity", default='Average', action="store",
                help="Max severity to show: Disaster, High, Average(default), Warning, Info")
optionparser.add_option("-n", "--no-colour", dest="noColour", default=False, action="store_true",
                help="Disable colours in the output")

(options, args) = optionparser.parse_args()

severities = ['Disaster', 'High', 'Average', 'Warning', 'Info']
hostname = socket.getfqdn()

sortedBySeverityTriggers = {}
for severity in severities:
    sortedBySeverityTriggers[severity] = []

if options.noColour:
    coloursForTriggers = { 'Time': '', 'Disaster': '', 'High': '', 'Average': '', 'Warning': '', 'Info': '', }
else:
    coloursForTriggers = {
        'Time': Style.BRIGHT + Fore.GREEN,
        'Disaster': Style.BRIGHT + Fore.RED,
        'High': Style.DIM + Fore.RED,
        'Average': Fore.YELLOW,
        'Warning': Fore.WHITE,
        'Info': Fore.BLUE
        }

longestTrigger = 0 # We will use this variable to count intend from time field

facter = Facter(['zabbix_triggers'])
triggers = facter.allFacts()['zabbix_triggers']
if triggers == 'false':
    print (coloursForTriggers['Time'] + "No alerts" + Style.RESET_ALL)
    sys.exit(0)

def humanTime(sec_elapsed):
    result = ''
    w = int(sec_elapsed / 604800)
    if w > 0: result += str(w) + "w " # weeks
    d = int((sec_elapsed % 604800) / 86400)
    if d > 0: result += str(d) + "d " # days
    h = int(((sec_elapsed % 604800) % 86400) / 3600)
    result += "{:>02}:".format(h) # hours will be shown as two digits, even if 00
    m = int((((sec_elapsed % 604800) % 86400) % 3600) / 60 )
    if m < 1: m = 1 # always show at least one minute, to avoid confusion
    result += "{:>02}".format(m)
    # We do not need seconds, update time is ~2 minutes anyway
    return result

for host in triggers.keys():
    triggersForHost = triggers[host]
    for trigger in triggersForHost.keys():
        if triggersForHost[trigger]['Time'] > longestTrigger: longestTrigger = triggersForHost[trigger]['Time']
        sortedBySeverityTriggers[triggersForHost[trigger]['Severity']].append(
                    {
                    'Trigger': trigger,
                    'Time': triggersForHost[trigger]['Time'],
                    'HostCname': host,
                    }
                )
longestTrigger = len(humanTime(longestTrigger)) # we need the length of the longest time string on a screen

for severity in severities:
    sortedBySeverityTriggers[severity] = sorted(sortedBySeverityTriggers[severity], key=itemgetter('Time'))
    for trigger in sortedBySeverityTriggers[severity]:
        print (coloursForTriggers['Time'] + "[" + humanTime(trigger['Time']) + "]" + Style.RESET_ALL),
        print (" " * (longestTrigger - len(humanTime(trigger['Time'])))), # intend triggers, so they look even
        print (coloursForTriggers[severity] + trigger['Trigger'] + Style.RESET_ALL),
        if trigger['HostCname'] != hostname:
            print ("(as " + trigger['HostCname'] + ")"),
        print ""
    if severity == options.maxSeverity: sys.exit(0)
