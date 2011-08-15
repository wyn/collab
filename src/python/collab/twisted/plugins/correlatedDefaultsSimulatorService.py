# Copyright (c) Simon Parry.
# See LICENSE for details.

from twisted.application.service import ServiceMaker
  
theService = ServiceMaker(
        "Collab Simulation Manager Service",
        "collab.tapfiles.correlatedDefaultsSimulator.tap",
        "A simulation manager service for the Collab system",
        "collab_simulations_manager")
