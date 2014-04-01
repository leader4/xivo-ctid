# -*- coding: utf-8 -*-

# Copyright (C) 2007-2014 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import logging
from xivo_cti.exception import NotAQueueException

logger = logging.getLogger("InnerdataDAO")


class InnerdataDAO(object):

    def __init__(self, innerdata):
        self.innerdata = innerdata

    def get_queue_id(self, queue_name):
        queue_id = self.innerdata.xod_config['queues'].idbyqueuename(queue_name)
        if queue_id is None:
            raise NotAQueueException('Queue name: %s' % queue_name)
        return queue_id

    def get_queue_ids(self):
        return self.innerdata.xod_config['queues'].get_queues()

    def get_presences(self, profile):
        profile_id = self.innerdata._config.getconfig('profiles').get(profile).get('userstatus')
        return self.innerdata._config.getconfig('userstatus').get(profile_id).keys()