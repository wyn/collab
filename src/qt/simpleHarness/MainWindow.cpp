// # Copyright (c) Simon Parry.
// # See LICENSE for details.

#include "MainWindow.h"
#include "ui_MainWindow.h"
#include "RegisterDialog.h"
#include "QXmppWrapper.h"
#include "ProgressDialog.h"
#include "QXmppIq.h""

#include <QAbstractButton>
#include <QFileDialog>
#include <QApplication>
#include <QDialog>
#include <QDebug>
#include <QMessageBox>
#include <QStringBuilder>


MainWindow::MainWindow(QWidget *parent) :
    QMainWindow(parent),
    ui(new Ui::MainWindow),
    xmppWrapper(new QXmppWrapper(this)),
    progressDialogs(),
    startTimes()
{
    ui->setupUi(this);
    ui->horizontalSlider->setValue(MainWindow::default_number_runs);
    ui->lineEdit_numberRuns->setText(QString::number(MainWindow::default_number_runs*MainWindow::run_factor));

    connect(ui->actionRegister, SIGNAL(triggered()), this, SLOT(onRegister_triggered()));
    connect(ui->actionUnregister, SIGNAL(triggered()), this, SLOT(onUnregister_triggered()));
    connect(ui->actionRun, SIGNAL(triggered()), this, SLOT(onRun_triggered()));

    connect(this->xmppWrapper, SIGNAL(connected()), this, SLOT(onConnected()));
    connect(this->xmppWrapper, SIGNAL(disconnected()), this, SLOT(onDisconnected()));
    connect(this->xmppWrapper, SIGNAL(error(QXmppClient::Error)), this, SLOT(onError(QXmppClient::Error)));

    connect(this->xmppWrapper, SIGNAL(started(QString)), this, SLOT(onStarted(QString)));
    connect(this->xmppWrapper, SIGNAL(cancelled(QString)), this, SLOT(onCancelled(QString)));
    connect(this->xmppWrapper, SIGNAL(progress(QString,int)), this, SLOT(onProgress(QString,int)));
    connect(this->xmppWrapper, SIGNAL(result(QString,QMap<double,double>)), this, SLOT(onResult(QString,QMap<double,double>)));

}

MainWindow::~MainWindow()
{
    // unregister if still registered
    delete ui;
}

void MainWindow::onConnected()
{
    // write to log
    const QXmppConfiguration &config(this->xmppWrapper->getConnection());
    ui->textEdit_logs->append(
            QString("Collab: connected - host [%1], port [%2], jid [%3]")
                .arg(config.host())
                .arg(config.port())
                .arg(config.jid())
                );

}

void MainWindow::onDisconnected()
{
    // write to log
    const QXmppConfiguration &config(this->xmppWrapper->getConnection());
    ui->textEdit_logs->append(
            QString("Collab: disconnected - host [%1], port [%2], jid [%3]")
                .arg(config.host())
                .arg(config.port())
                .arg(config.jid())
                );
}

void MainWindow::onError(const QXmppClient::Error &err)
{
    // write to log
    QString error("unknown");
    switch (err) {
    case QXmppClient::SocketError: {
            error = "socket error";
            break;
        }
    case QXmppClient::KeepAliveError: {
            error = "keep alive error";
            break;
        }
    case QXmppClient::XmppStreamError: {
            error = "xmpp stream error";
            break;
        }
    default:
        break;
    }

    ui->textEdit_logs->append(QString("XMPP Error: %1").arg(error));
}

void MainWindow::onStarted(const QString &id)
{
    if (progressDialogs.contains(id)) {
        qWarning() << "Already running: " << id;
        return;
    }

    ui->textEdit_logs->append(QString("Collab: started run [%1]").arg(id));
    ui->lineEdit_Identifier->setText(id);

    ProgressDialog *progress(new ProgressDialog(this));
    progress->setLabel(id);
    connect(progress, SIGNAL(cancelled(QString)), this, SLOT(onCancelled(QString)));
    this->progressDialogs.insert(id, progress);

    // set start time
    this->startTimes[id] = QDateTime::currentDateTime();
    // make portfolio and run details
//    this->xmppWrapper->start(details);
    progress->exec();
}

void MainWindow::onCancelled(const QString &id)
{
    if (!this->progressDialogs.contains(id)) {
        qWarning() << "Not running: " << id;
        return;
    }

    ui->textEdit_logs->append(QString("Collab: cancelled [%1]").arg(id));
    this->xmppWrapper->cancel(id);
    // set time taken
    if (this->startTimes.contains(id)) {
        const QDateTime t(this->startTimes[id]);
        int dt = t.secsTo(QDateTime::currentDateTime());
        ui->lineEdit_timeTaken->setText(QString::number(dt));
    }

    this->progressDialogs.remove(id);
}

void MainWindow::onProgress(const QString &id, int progress)
{
    if (!progressDialogs.contains(id)) {
        qWarning() << "Not running: " << id;
        return;
    }
    // update progress dialog for id
    ProgressDialog *p = this->progressDialogs[id];
    p->updateProgress(progress);
}

void MainWindow::onResult(const QString &id, const QMap<double, double> &percentiles)
{
    if (!progressDialogs.contains(id)) {
        qWarning() << "Not running: " << id;
        return;
    }
    ui->textEdit_logs->append(QString("Collab: finished [%1]").arg(id));
    // set time taken
    if (this->startTimes.contains(id)) {
        const QDateTime t(this->startTimes[id]);
        int dt = t.secsTo(QDateTime::currentDateTime());
        ui->lineEdit_timeTaken->setText(QString::number(dt));
    }
    if (percentiles.contains(0.99)) {
        ui->lineEdit_99perc->setText(QString::number(percentiles[0.99]));
    }
    if (percentiles.contains(0.95)) {
        ui->lineEdit_95perc->setText(QString::number(percentiles[0.95]));
    }

    // set final progress
    this->onProgress(id, 100);
    this->progressDialogs.remove(id);

}

void MainWindow::on_toolButton_setInput_clicked()
{
    QString filename = QFileDialog::getOpenFileName(this, "Input File", QApplication::applicationDirPath(), tr("Portfolios (*.xml)"));
    if (filename == "") {
        return;
    }

    ui->lineEdit_input->setText(filename);

}

void MainWindow::on_toolButton_viewInput_clicked()
{
    QMessageBox::information(this, "Not implemented", "This is not implemented yet");

}

void MainWindow::on_toolButton_setOutput_clicked()
{
    QString filename = QFileDialog::getSaveFileName(this, "Save Output To", QApplication::applicationDirPath());
    if (filename == "") {
        return;
    }

    ui->lineEdit_output->setText(filename);

}

void MainWindow::on_toolButton_viewOutput_clicked()
{
    QMessageBox::information(this, "Not implemented", "This is not implemented yet");

}

void MainWindow::on_buttonBox_clicked(QAbstractButton* button)
{
    // ok and cancel dealt with above
    switch (ui->buttonBox->buttonRole(button)) {

    case QDialogButtonBox::AcceptRole: {
            qDebug() << "Accepted";
            this->onRun_triggered();
        }
        break;

    case QDialogButtonBox::ResetRole: {
            qDebug() << "Reset";
            QListIterator<QLineEdit *> it(ui->centralWidget->findChildren<QLineEdit *>());
            while (it.hasNext()) {
                QLineEdit *const w(it.next());
                qDebug() << "Line edit: " << w->text();
                w->setText("");
            }
            ui->horizontalSlider->setValue(MainWindow::default_number_runs);
            ui->lineEdit_numberRuns->setText(QString::number(MainWindow::default_number_runs*MainWindow::run_factor));
        }
        break;

    default: {
            qDebug() << "MainWindow: unhandled button pressed: " << button->text();
        }
        break;

    }

}

void MainWindow::on_horizontalSlider_valueChanged(int value)
{
    ui->lineEdit_numberRuns->setText(QString::number(value*MainWindow::run_factor));
}

void MainWindow::onRegister_triggered()
{
    // try and open an XMPP connection with collab.coshx
    RegisterDialog r;
    switch(r.exec()) {
    case QDialog::Accepted: {
            // OK was pressed
            qDebug() << "Accepted connection config:";
            const QXmppConfiguration &config(r.getConfiguration());
            qDebug() << "Host: " << config.host();
            qDebug() << "Port: " << config.port();
            qDebug() << "JID: " << config.jid();
            qDebug() << "Password: " << config.password();
            this->xmppWrapper->connectToServer(config);
        }
    default: {
        }

    }

}

void MainWindow::onUnregister_triggered()
{
    qDebug() << "Unregistering";
    this->xmppWrapper->disconnectFromServer();
}

void MainWindow::onRun_triggered()
{
    if (!this->xmppWrapper->isConnected()) {
        this->onRegister_triggered();
    }
    else {
        const QXmppConfiguration &config(r.getConfiguration());
        QXmppIq details(QXmppIq::Set);

        // make portfolio stanza and send off to be run
        this->xmppWrapper->start(details);
    }
}

