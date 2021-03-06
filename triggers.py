#!/local/python/bin/python

from efacter import Facter
import json, sys, socket, urllib2
from optparse import OptionParser
from colorama import Fore, Back, Style
from pygments.lexers import JsonLexer
from pygments.formatters import TerminalFormatter
from pygments.styles import native
from operator import itemgetter
import dns.resolver

def getSettings():
    usage = "usage: %prog [-n]"
    optionparser = OptionParser(usage=usage)
    optionparser.add_option("-s", "--max-severity", dest="maxSeverity", default='Average', action="store",
            help="Max severity to show: Disaster, High, Average(default), Warning, Info")
    optionparser.add_option("-n", "--no-colour", dest="noColour", default=False, action="store_true",
            help="Disable colours in the output")
    (options, args) = optionparser.parse_args()
    localFQDN = socket.getfqdn()
    coloursForTriggers = {
        'Time': Style.BRIGHT + Fore.GREEN if not options.noColour else '',
        'Disaster': Style.BRIGHT + Fore.RED if not options.noColour else '',
        'High': Style.DIM + Fore.RED if not options.noColour else '',
        'Average': Fore.YELLOW if not options.noColour else '',
        'Warning': Fore.WHITE if not options.noColour else '',
        'Info': Fore.BLUE if not options.noColour else '',
        } 
    if len(args) == 0:
        remoteHost = False
        targetFQDN = localFQDN
    else:
        if len(args) > 1:
            optionparser.error("You can provide only one optional argument: FQDN")
        elif args[0] == localFQDN:
            remoteHost = False
            targetFQDN = localFQDN
        else:
            remoteHost = args[0]
            targetFQDN = remoteHost
    return options, remoteHost, targetFQDN, coloursForTriggers


def getLocalTriggers():
    facter = Facter(['zabbix_triggers'])
    triggers = facter.allFacts()['zabbix_triggers']
    return triggers

def getRemoteTriggers(remoteHost):
    DNS = checkDNSName(remoteHost)
    if DNS == "NXDOMAIN":
        print >> sys.stderr, "There is no such domain: " + remoteHost
        sys.exit(1)
    else:
        remoteHost = str(DNS).rstrip('.')
    url = "http://zbx.mlan/triggers/"+remoteHost+".json"
    HTTPResponce = urllib2.urlopen(url)
    file_stream = HTTPResponce.read().rstrip('\n')
    try:
        json_fact = json.loads(file_stream)
    except ValueError, e:
        print >> sys.stderr, "Can't load triggers"
        sys.exit(1)
    return json_fact['zabbix_triggers']

def checkDNSName(name):
    try:
        answer = dns.resolver.query(name)
    except dns.resolver.NXDOMAIN:
        return "NXDOMAIN"
    return answer.canonical_name

def secondsToHumanTime(sec_elapsed):
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


def sortTriggersBySeverity (triggers, severities):
    sortedBySeverityTriggers = {severity: []
            for severity in severities}
    for host, triggersForHost in triggers.iteritems():
        for trigger, triggerProperties in triggersForHost.iteritems():
            humanTime = secondsToHumanTime(triggerProperties['Time'])
            sortedBySeverityTriggers[triggerProperties['Severity']].append(
                    {
                        'Trigger': trigger,
                        'Time': triggerProperties['Time'],
                        'HumanTime': humanTime,
                        'HostCname': host,
                    }
                )
    for severity in severities:
        sortedBySeverityTriggers[severity] = sorted(sortedBySeverityTriggers[severity], key=itemgetter('Time'))
    return sortedBySeverityTriggers

def main():
    severities = ['Disaster', 'High', 'Average', 'Warning', 'Info']
    (options, remoteHost, targetFQDN, coloursForTriggers) = getSettings()
    triggers = getRemoteTriggers(targetFQDN) if remoteHost else getLocalTriggers()
    if triggers == 'false':
        print (coloursForTriggers['Time'] + "No alerts" + Style.RESET_ALL)
        sys.exit(0)
    sortedBySeverityTriggers = sortTriggersBySeverity (triggers, severities)

    longestTrigger = 0 # We will use this variable to count padding length
    for severity in severities:
        for trigger in sortedBySeverityTriggers[severity]:
            if len(trigger['HumanTime']) > longestTrigger:
                longestTrigger = len(trigger['HumanTime'])
        if severity == options.maxSeverity:
            break

    triggerDisplayedCounter = 0 # Did we actially show anything?
    for severity in severities:
        for trigger in sortedBySeverityTriggers[severity]:
            print (coloursForTriggers['Time'] + "[" + trigger['HumanTime'] + "]" + Style.RESET_ALL),
            print (" " * (longestTrigger - len(trigger['HumanTime']))), # intend triggers for prettier output
            print (coloursForTriggers[severity] + trigger['Trigger'] + Style.RESET_ALL),
            if trigger['HostCname'] != targetFQDN:
                print ("(as " + trigger['HostCname'] + ")"),
            print "" # \n
            triggerDisplayedCounter += 1
        if severity == options.maxSeverity:
            if triggerDisplayedCounter < 1: # If we didn't show anything, let's tell about other, less severe, triggers
                print (coloursForTriggers['Time'] + "No alerts" + Style.RESET_ALL)
                print "+triggers with severity below %s" % options.maxSeverity
            sys.exit(0)

if __name__ == "__main__":
    sys.exit(main())
