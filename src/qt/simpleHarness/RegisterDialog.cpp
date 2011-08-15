// # Copyright (c) Simon Parry.
// # See LICENSE for details.

#include "RegisterDialog.h"
#include "ui_RegisterDialog.h"
#include "QXmppConfiguration.h"

RegisterDialog::RegisterDialog(QWidget *parent) :
    QDialog(parent),
    ui(new Ui::RegisterDialog),
    config(new QXmppConfiguration())
{
    ui->setupUi(this);
    ui->lineEdit_host->setText("www.coshx.co.uk");
    ui->lineEdit_port->setText("5222");
    ui->lineEdit_jid->setText(tr("simon@collab.coshx"));
}

RegisterDialog::~RegisterDialog()
{
    delete config;
    delete ui;    
}


void RegisterDialog::on_buttonBox_accepted()
{
    config->setHost(ui->lineEdit_host->text());
    config->setPort(ui->lineEdit_port->text().toInt());
    config->setJid(ui->lineEdit_jid->text());
    config->setPassword(ui->lineEdit_password->text());
    this->close();
}

void RegisterDialog::on_buttonBox_rejected()
{
    this->close();
}

const QXmppConfiguration &RegisterDialog::getConfiguration() const
{
    return *config;
}
