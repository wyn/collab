// # Copyright (c) Simon Parry.
// # See LICENSE for details.

#include "QXmppWrapper.h"
#include "QXmppLogger.h"
#include "QXmppIq.h"
#include "QXmppConfiguration.h"
#include "QXmppStanza.h"

QXmppWrapper::QXmppWrapper(QObject *parent) :
    QObject(parent),
    xmpp(new QXmppClient(this))
{
    QXmppLogger::getLogger()->setLoggingType(QXmppLogger::StdoutLogging);
    // pass through signals
    connect(xmpp, SIGNAL(connected()), this, SIGNAL(connected()));
    connect(xmpp, SIGNAL(disconnected()), this, SIGNAL(disconnected()));
    connect(xmpp, SIGNAL(error(QXmppClient::Error)), this, SIGNAL(error(const QXmppClient::Error &)));

    // other connections
    connect(xmpp, SIGNAL(iqReceived(QXmppIq)), this, SLOT(onIqReceived(const QXmppIq &)));

}

void QXmppWrapper::connectToServer(
        const QXmppConfiguration& config,
        const QXmppPresence& initialPresence
        )
{
    xmpp->connectToServer(config, initialPresence);
}

void QXmppWrapper::disconnectFromServer()
{
    xmpp->disconnectFromServer();
}

void QXmppWrapper::start(const QXmppStanza &details)
{
    // send details to collab as a start action
}

void QXmppWrapper::cancel(const QString &id)
{
    // send cancel command to collab
}

void QXmppWrapper::onIqReceived(const QXmppIq &iq)
{
    // disect iq and emit appropriate bits with
    // this.started, this.cancelled, this.progress, this.result
}
