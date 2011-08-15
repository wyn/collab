// # Copyright (c) Simon Parry.
// # See LICENSE for details.

#ifndef REGISTERDIALOG_H
#define REGISTERDIALOG_H

#include <QDialog>

class QXmppConfiguration;

namespace Ui {
    class RegisterDialog;
}

class RegisterDialog : public QDialog
{
    Q_OBJECT

public:
    explicit RegisterDialog(QWidget *parent = 0);
    ~RegisterDialog();
    const QXmppConfiguration &getConfiguration() const;

private:
    Ui::RegisterDialog *ui;
    QXmppConfiguration *config;


private slots:
    void on_buttonBox_accepted();
    void on_buttonBox_rejected();
};

#endif // REGISTERDIALOG_H
