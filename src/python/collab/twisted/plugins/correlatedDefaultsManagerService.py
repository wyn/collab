# Copyright (c) Simon Parry.
# See LICENSE for details.

from twisted.application.service import ServiceMaker
  
theService = ServiceMaker(
        "Collab Portfolio Manager Service",
        "collab.tapfiles.correlatedDefaultsManager.tap",
        "A portfolio manager service for the Collab system",
        "collab_portfolios_manager")
