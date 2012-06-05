# vim: set fileencoding=utf-8 :
# xivo-ctid

# Copyright (C) 2007-2012  Avencall
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# Alternatively, XiVO CTI Server is available under other licenses directly
# contracted with Avencall. See the LICENSE file at top of the source tree
# or delivered in the installable package in which XiVO CTI Server is
# distributed for more details.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Asterisk AMI utilities.
"""

import logging
import socket
import string
import time

from xivo_cti.tools.extension import normalize_exten

logger = logging.getLogger('xivo_ami')

ALPHANUMS = string.uppercase + string.lowercase + string.digits

switch_originates = True


class AMIClass(object):
    class AMIError(Exception):
        def __init__(self, msg):
            self.msg = msg

        def __str__(self):
            return self.msg

    def __init__(self, ipbxid, ipaddress, ipport, loginname, password, events):
        self.ipbxid = ipbxid
        self.ipaddress = ipaddress
        self.ipport = ipport
        self.loginname = loginname
        self.password = password
        self.events = events
        self.actionid = None

    def connect(self):
        self.actionid = None
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sockret = self.sock.connect_ex((self.ipaddress, self.ipport))
        if sockret:
            logger.warning('unable to connect to %s:%d - reason %d',
                           self.ipaddress, self.ipport, sockret)
        else:
            self.sock.settimeout(30)
            self.fd = self.sock.fileno()

    def sendcommand(self, action, args, loopnum=0):
        ret = False
        try:
            t0 = time.time()
            towritefields = ['Action: %s' % action]
            for (name, value) in args:
                try:
                    towritefields.append('%s: %s' % (name, value))
                except Exception:
                    logger.exception('(sendcommand build %s : %s = %s (%r))',
                                     action, name, value, value)
            if self.actionid:
                towritefields.append('ActionId: %s' % self.actionid)
            towritefields.append('\r\n')

            rawstr = '\r\n'.join(towritefields)
            if isinstance(rawstr, unicode):
                ustr = rawstr.encode('utf8')
            else:
                ustr = rawstr
            self.sock.sendall(ustr)
            ret = True
        except UnicodeEncodeError:
            logger.exception('(sendcommand UnicodeEncodeError (%s %s %s))',
                             towritefields, self.actionid, self.fd)
            ret = True
        except UnicodeDecodeError:
            logger.exception('(sendcommand UnicodeDecodeError (%s %s %s))',
                             action, self.actionid, self.fd)
            ret = True
        except socket.timeout:
            t1 = time.time()
            logger.exception('(sendcommand timeout (%s %s %s) timespent=%f)',
                             action, self.actionid, self.fd, (t1 - t0))
            ret = False
        except Exception:
            t1 = time.time()
            logger.exception('(sendcommand other (%s %s %s) timespent=%f)',
                             action, self.actionid, self.fd, (t1 - t0))
            ret = False
        if ret == False:
            if loopnum == 0:
                logger.warning('second attempt for AMI command (%s %s %s)',
                               action, self.actionid, self.fd)
                # tries to reconnect
                try:
                    self.sock.close()

                    self.connect()
                    self.login()
                    if self:
                        # "retrying AMI command=<%s> args=<%s>" % (action, str(args)))
                        self.sendcommand(action, args, 1)
                except Exception:
                    logger.exception('reconnection (%s %s %s)',
                                     action, self.actionid, self.fd)
            else:
                logger.warning('2 attempts have failed for AMI command (%s %s %s)',
                               action, self.actionid, self.fd)
        if self.actionid:
            self.actionid = None
        return ret

    def setactionid(self, actionid):
        self.actionid = actionid

    def _exec_command(self, *args):
        try:
            return self.sendcommand(*args)
        except self.AMIError:
            return False
        except Exception:
            return False

    def sendqueuestatus(self, queue=None):
        if queue is None:
            return self._exec_command('QueueStatus', [])
        else:
            return self._exec_command('QueueStatus',
                                      [('Queue', queue)])

    # \brief Requesting an ExtensionState.
    def sendextensionstate(self, exten, context):
        return self._exec_command('ExtensionState',
                                  [('Exten', exten),
                                   ('Context', context)])

    def sendparkedcalls(self):
        return self._exec_command('ParkedCalls', [])

    def sendmeetmelist(self):
        return self._exec_command('MeetMeList', [])

    # \brief Logins to the AMI.
    def login(self):
        if self.events:
            onoff = 'on'
        else:
            onoff = 'off'
        return self._exec_command('Login',
                                  [('Username', self.loginname),
                                   ('Secret', self.password),
                                   ('Events', onoff)])

    def hangup(self, channel, channel_peer=None):
        ret = 0
        self._exec_command('Hangup',
                           [('Channel', channel)])
        ret += 1

        if channel_peer:
            self._exec_command('Hangup',
                               [('Channel', channel_peer)])
            ret += 2
        return ret

    def setvar(self, var, val, chan=None):
        if chan is None:
            return self._exec_command('Setvar', [('Variable', var),
                                                 ('Value', val)])
        else:
            return self._exec_command('Setvar', [('Channel', chan),
                                                 ('Variable', var),
                                                 ('Value', val)])

    def origapplication(self, application, data, phoneproto, phonesrcname, phonesrcnum, context):
        return self._exec_command('Originate', [('Channel', '%s/%s' % (phoneproto, phonesrcname)),
                                                ('Context', context),
                                                ('Priority', '1'),
                                                ('Application', application),
                                                ('Data', data),
                                                ('Variable', 'XIVO_ORIGACTIONID=%s' % self.actionid),
                                                ('Variable', 'XIVO_ORIGAPPLI=%s' % application),
                                                ('Async', 'true')])

    # \brief Originates a call from a phone towards another.
    def originate(self, phoneproto, phonesrcname, phonesrcnum, cidnamesrc,
                  phonedst, cidnamedst,
                  locext, extravars={}, timeout=3600):
        # originate a call btw src and dst
        # src will ring first, and dst will ring when src responds
        try:
            phonedst = normalize_exten(phonedst)
            if phoneproto == 'custom':
                channel = phonesrcname.replace('\\', '')
            else:
                channel = '%s/%s' % (phoneproto, phonesrcname)
            command_details = [('Channel', channel),
                               ('Exten', phonedst),
                               ('Context', locext),
                               ('Priority', '1'),
                               ('Timeout', str(timeout * 1000)),
                               ('Variable', 'XIVO_ORIGAPPLI=%s' % 'OrigDial'),
                               ('Async', 'true')]
            if switch_originates:
                if (phonedst.startswith('#')):
                    command_details.append(('CallerID', '"%s"' % cidnamedst))
                else:
                    command_details.append(('CallerID', '"%s"<%s>' % (cidnamedst, phonedst)))
            else:
                command_details.append(('CallerID', '"%s"' % cidnamesrc))
            for var, val in extravars.iteritems():
                command_details.append(('Variable', '%s=%s' % (var, val)))
            command_details.append(('Variable', 'XIVO_ORIGACTIONID=%s' % self.actionid))
        except Exception, e:
            logger.warning('Originate failed: %s', e.message)
            return False
        return self._exec_command('Originate', command_details)

    # \brief Requests the Extension Statuses
    def extensionstate(self, extension, context):
        return self._exec_command('ExtensionState', [('Exten', extension),
                                                     ('Context', context)])

    # \brief Logs in an Agent
    def agentcallbacklogin(self, agentnum, extension, context, ackcall):
        return self._exec_command('AgentCallbackLogin', [('Agent', agentnum),
                                                         ('Context', context),
                                                         ('Exten', extension),
                                                         ('AckCall', ackcall)])

    # \brief Logs off an Agent
    def agentlogoff(self, agentnum, soft=True):
        return self._exec_command('AgentLogoff', [('Agent', agentnum),
                                                  ('Soft', soft)])

    # \brief Mute a meetme user
    def meetmemute(self, meetme, usernum):
        return self._exec_command('MeetmeMute', (('Meetme', meetme),
                                                 ('Usernum', usernum)))

    # \brief Unmute a meetme user
    def meetmeunmute(self, meetme, usernum):
        return self._exec_command('MeetmeUnmute', (('Meetme', meetme),
                                                   ('Usernum', usernum)))

    def meetmemoderation(self, command, meetme, usernum, adminnum):
        return self._exec_command(command, (('Meetme', meetme),
                                            ('Usernum', usernum),
                                            ('Adminnum', adminnum)))

    def meetmepause(self, meetme, status):
        return self._exec_command('MeetmePause', (('Meetme', meetme),
                                                  ('Status', status)))

    def queueadd(self, queuename, interface, paused, skills=''):
        # it looks like not specifying Paused is the same as setting it to false
        return self._exec_command('QueueAdd', [('Queue', queuename),
                                               ('Interface', interface),
                                               ('Penalty', '1'),
                                               ('Paused', paused),
                                               ('Skills', skills)])

    # \brief Removes a Queue
    def queueremove(self, queuename, interface):
        return self._exec_command('QueueRemove', [('Queue', queuename),
                                                  ('Interface', interface)])

    # \brief (Un)Pauses a Queue
    def queuepause(self, queuename, interface, paused):
        return self._exec_command('QueuePause', [('Queue', queuename),
                                                 ('Interface', interface),
                                                 ('Paused', paused)])

    def queuepauseall(self, interface, paused):
        return self._exec_command('QueuePause', [('Interface', interface),
                                                 ('Paused', paused)])

    # \brief Logs a Queue Event
    def queuelog(self, queuename, event,
                 uniqueid=None,
                 interface=None,
                 message=None):
        command_details = [('Queue', queuename),
                           ('Event', event)]
        if uniqueid:
            command_details.append(('Uniqueid', uniqueid))
        if interface:
            command_details.append(('Interface', interface))
        if message:
            command_details.append(('Message', message))
        return self._exec_command('QueueLog', command_details)

    def queuesummary(self, queuename=None):
        if (queuename is None):
            return self._exec_command('QueueSummary', [])
        else:
            return self._exec_command('QueueSummary', [('Queue', queuename)])

    # \brief Requests the Mailbox informations
    def mailbox(self, phone, context):
        ret1 = self._exec_command('MailboxCount', [('Mailbox', '%s@%s' % (phone, context))])
        ret2 = self._exec_command('MailboxStatus', [('Mailbox', '%s@%s' % (phone, context))])
        ret = ret1 and ret2
        return ret

    # \brief Starts monitoring a channel
    def monitor(self, channel, filename, mixme='true'):
        return self._exec_command('Monitor',
                                  [('Channel', channel),
                                   ('File', filename),
                                   ('Mix', mixme)])

    # \brief Stops monitoring a channel
    def stopmonitor(self, channel):
        return self._exec_command('StopMonitor',
                                  [('Channel', channel)])

    # \brief Retrieves the value of Variable in a Channel
    def getvar(self, channel, varname):
        return self._exec_command('Getvar', [('Channel', channel),
                                             ('Variable', varname)])

    # \brief Sends a sipnotify
    def sipnotify(self, *variables):
        channel = variables[0]
        arglist = [('Variable', '%s=%s' % (k, v.replace('"', '\\"')))
            for k, v in variables[len(variables) - 1].iteritems()]
        arglist.append(('Channel', channel))
        return self._exec_command('SIPNotify', arglist)

    # \brief Request a mailbox count
    # context is for tracking only
    def mailboxcount(self, mailbox, context=None):
        return self._exec_command('MailboxCount', (('MailBox', mailbox),))

    # \brief Transfers a channel towards a new extension.
    def transfer(self, channel, extension, context):
        try:
            extension = normalize_exten(extension)
        except ValueError, e:
            logger.warning('Transfer failed: %s', e.message)
            return False
        else:
            command_details = [('Channel', channel),
                               ('Exten', extension),
                               ('Context', context),
                               ('Priority', '1')]
        return self._exec_command('Redirect', command_details)

    # \brief Atxfer a channel towards a new extension.
    def atxfer(self, channel, extension, context):
        try:
            extension = normalize_exten(extension)
        except ValueError, e:
            logger.warning('Attended transfer failed: %s', e.message)
            return False
        else:
            return self._exec_command('Atxfer', [('Channel', channel),
                                                 ('Exten', extension),
                                                 ('Context', context),
                                                 ('Priority', '1')])

    def txfax(self, faxpath, userid, callerid, number, context):
        # originate a call btw src and dst
        # src will ring first, and dst will ring when src responds
        try:
            ret = self.sendcommand('Originate', [('Channel', 'Local/%s@%s' % (number, context)),
                                                 ('CallerID', callerid),
                                                 ('Variable', 'XIVO_FAX_PATH=%s' % faxpath),
                                                 ('Variable', 'XIVO_USERID=%s' % userid),
                                                 ('Context', 'txfax'),
                                                 ('Exten', 's'),
                                                 ('Async', 'true'),
                                                 ('Priority', '1')])
            return ret
        except self.AMIError:
            return False
        except socket.timeout:
            return False
        except socket:
            return False
        except Exception:
            return False
