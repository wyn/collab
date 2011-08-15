# Copyright (c) Simon Parry.
# See LICENSE for details.

from twisted.application.service import ServiceMaker
  
collabProxyVarService = ServiceMaker(
        "Collab Proxy VaR Service",
        "collab.tapfiles.collabProxyVar.tap",
        "A proxy service for the Collab system VaR calculation",
        "collab_proxy_var")

