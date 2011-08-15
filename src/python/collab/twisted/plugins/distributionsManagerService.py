# Copyright (c) Simon Parry.
# See LICENSE for details.

from twisted.application.service import ServiceMaker
  
theService = ServiceMaker(
        "Collab Distributions Manager Service",
        "collab.tapfiles.distributionsManager.tap",
        "A distributions manager service for the Collab system",
        "collab_distributions_manager")
