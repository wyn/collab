# Copyright (c) Simon Parry.
# See LICENSE for details.

from twisted.application.service import ServiceMaker

collabSystemManagerService = ServiceMaker(
        "Collab System Manager Service",
        "collab.tapfiles.collabSystemManager.tap", # the module that should contain Options and makeService
        "A system manager service for the Collab system",
        "collab_system_manager") # the tapname
