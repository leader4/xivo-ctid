# vim: set fileencoding=utf-8 :
# xivo-ctid

# Copyright (C) 2007-2011  Avencall
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# Alternatively, XiVO CTI Server is available under other licenses directly
# contracted with Pro-formatique SARL. See the LICENSE file at top of the
# source tree or delivered in the installable package in which XiVO CTI Server
# is distributed for more details.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
from xivo_cti.ami import ami_callback_handler

logger = logging.getLogger("AMIAgentLogin")


class AMIAgentLoginLogoff(object):
    _instance = None

    def __init__(self):
        pass

    def _build_agent_id_from_event(self, event):
        return 'Agent/%s' % event['Agent']

    def on_event_agent_login(self, event):
        agent_id = self._build_agent_id_from_event(event)
        self.queue_statistics_producer.on_agent_loggedon(agent_id)

    def on_event_agent_logoff(self, event):
        agent_id = self._build_agent_id_from_event(event)
        self.queue_statistics_producer.on_agent_loggedoff(agent_id)

    @classmethod
    def register_callbacks(cls):
        callback_handler = ami_callback_handler.AMICallbackHandler.get_instance()
        ami_agent_login = cls.get_instance()
        callback_handler.register_callback('Agentcallbacklogin', ami_agent_login.on_event_agent_login)
        callback_handler.register_callback('Agentcallbacklogoff', ami_agent_login.on_event_agent_logoff)

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            cls._instance = cls()
        return cls._instance
