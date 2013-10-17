# -*- coding: utf-8 -*-

# Copyright (C) 2007-2013 Avencall
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


from xivo_cti.services.device.controller.aastra import AastraController
from xivo_dao.data_handler.device import services as device_services
from xivo_dao.data_handler.exception import ElementNotExistsError

POPC_DEVICES = {
    'Aastra': ['6731i', '6757i', '6755i'],
}


class DeviceManager(object):

    def __init__(self, ami_class):
        self.aastra_controller = AastraController(ami_class)

    def answer(self, device_id):
        try:
            device = device_services.get(device_id)
        except ElementNotExistsError:
            return

        if self._is_supported_device(device):
            self.aastra_controller.answer(device)

    def _is_supported_device(self, device):
        return device.model in POPC_DEVICES.get(device.vendor, [])
