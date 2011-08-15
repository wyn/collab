// # Copyright (c) Simon Parry.
// # See LICENSE for details.

#include "ProgressDialog.h"
#include "ui_ProgressDialog.h"

ProgressDialog::ProgressDialog(QWidget *parent) :
    QDialog(parent),
    ui(new Ui::ProgressDialog)
{
    ui->setupUi(this);
    connect(this, SIGNAL(destroyed()), this, SIGNAL(cancelled()));
}

ProgressDialog::~ProgressDialog()
{
    delete ui;
}

void ProgressDialog::on_pushButton_cancel_clicked()
{
    emit this->cancelled(ui->label_id->text());
    this->close();
}

void ProgressDialog::on_progressBar_valueChanged(int value)
{
    if (value >= ui->progressBar->maximum()) {
        this->close();
    }
}

void ProgressDialog::updateProgress(int value)
{
    ui->progressBar->setValue(value);
}

void ProgressDialog::setLabel(const QString &id)
{
    ui->label_id->setText(id);
}
