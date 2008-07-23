# XIVO Daemon

__version__   = '$Revision$'
__date__      = '$Date$'
__copyright__ = 'Copyright (C) 2007, 2008, Proformatique'
__author__    = 'Corentin Le Gall'

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Alternatively, XIVO Daemon is available under other licenses directly
# contracted with Pro-formatique SARL. See the LICENSE file at top of the
# source tree or delivered in the installable package in which XIVO Daemon
# is distributed for more details.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, you will find one at
# <http://www.gnu.org/licenses/old-licenses/gpl-2.0.html>.

from xivo_log import *
from xivo_ctiservers.cti_anylist import AnyList

def log_debug(level, text):
        log_debug_file(level, text, 'queuelist')
        return

class QueueList(AnyList):
        def __init__(self, newurls = []):
                AnyList.__init__(self, newurls)
                self.queuelist = {}
                return
        
        def update(self):
                for url, urllist in self.requested_list.iteritems():
                        gl = urllist.getlist(1, 5, True)
                        newqueuelist = self.commandclass.getqueueslist(urllist.list)
                        for a, b in newqueuelist.iteritems():
                                if a not in self.queuelist:
                                        self.queuelist[a] = b
                return

        def findqueue(self, queuename):
                if queuename in self.queuelist:
                        return self.queuelist.get(queuename)
                else:
                        return None
