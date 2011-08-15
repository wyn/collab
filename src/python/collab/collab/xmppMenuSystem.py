# Copyright (c) Simon Parry.
# See LICENSE for details.

from wokkel import disco

import collab


INFO_FEATURE = disco.DiscoFeature(disco.NS_DISCO_INFO)
ITEMS_FEATURE = disco.DiscoFeature(disco.NS_DISCO_ITEMS)
COMMAND_FEATURE = disco.DiscoFeature(collab.COMMAND_NS)
COMMAND_NODE = 'command-node'

class XmppMenuSystem(object):
    """
    Trying to simplify the creation of XMPP command menus
    """
    def __init__(self, entity, nodeIdentifier, category='component', idType='generic', name=''):
        """
        menus is a mapping of nodeIdentifier to (info, item, parent)
        """
        self.menus = dict()
        self._addTriple(entity, nodeIdentifier, category, idType, name, None)
        self.top = nodeIdentifier

    def addSubMenu(self, entity, nodeIdentifier, parentNodeIdentifier='', category='component', idType='generic', name=''):
        if nodeIdentifier in self.menus:
            raise KeyError('nodeIdentifier %s already present' % nodeIdentifier)

        parent = parentNodeIdentifier or self.top
        if parent not in self.menus.keys():
            raise KeyError('parent %s not present' % parent)

        self._addTriple(entity, nodeIdentifier, category, idType, name, parent)


    def _addTriple(self, entity, nodeIdentifier, category, idType, name, parent):
        info = disco.DiscoInfo()
        info.nodeIdentifier = nodeIdentifier
        info.append(disco.DiscoIdentity(
            category=category,
            idType=idType,
            name=name
            ))
        info.append(INFO_FEATURE)
        info.append(ITEMS_FEATURE)
        if idType==COMMAND_NODE:
            info.append(COMMAND_FEATURE)

        item = disco.DiscoItem(
            entity=entity,
            nodeIdentifier=nodeIdentifier,
            name=name
            )
            
        self.menus[nodeIdentifier] = (info, item, parent)
        
    def getChildItems(self, parent):
        if parent not in self.menus.keys():
            raise KeyError('parent %s not present' % parent)

        items = disco.DiscoItems()
        for info, item, p in self.menus.itervalues():
            if p == parent:
                items.append(item)

        return items
    
    # container stuff, NOTE there is no __setitem__, use addSubMenu

    def __len__(self):
        return len(self.menus)

    def __contains__(self, item):
        return item in self.menus

    def __iter__(self):
        return iter(self.menus)

    def __getitem__(self, key):
        return self.menus[key]

    def __delitem__(self, key):
        if key in self.menus:
            del self.menus[key]
    
