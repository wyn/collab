// # Copyright (c) Simon Parry.
// # See LICENSE for details.

#ifndef QXMPPWRAPPER_H
#define QXMPPWRAPPER_H

#include <QObject>

#include "QXmppPresence.h"
#include "QXmppClient.h"

class QXmppConfiguration;
class QXmppStanza;

class QXmppWrapper : public QObject
{
    Q_OBJECT
public:
    explicit QXmppWrapper(QObject *parent = 0);

    void connectToServer(const QXmppConfiguration&,
                         const QXmppPresence& initialPresence = QXmppPresence());

    void disconnectFromServer();

signals:
    /// emitted when the xmpp server connection is established
    void connected();

    /// emitted when the xmpp server disconnects
    void disconnected();

    /// emitted on errors with the xmlstream
    void error(const QXmppClient::Error &err);

    /// emitted when a simulation is started,
    /// the id is the identifier for the run
    void started(const QString &id);

    /// emitted when a run is cancelled,
    /// the run that was cancelled is identified by id
    void cancelled(const QString &id);

    /// emitted when progress information is available
    /// the id is the run identifier
    /// progress is the number of runs completed
    void progress(const QString &id, int progress);

    /// a result for a run with identifier id,
    /// the results are given as a map of percentiles to probability
    /// signifies the end of the run too
    void result(const QString &id, const QMap<double, double> &percentiles);

public slots:
    void start(const QXmppStanza &details);
    void cancel(const QString &id);

    void onIqReceived(const QXmppIq &iq);

public:
    const QXmppConfiguration &getConnection() const {
        return this->xmpp->configuration();
    }

    bool isConnected() const {
        return this->xmpp->isConnected();
    }

private:
    QXmppClient *xmpp;

};

#endif // QXMPPWRAPPER_H
