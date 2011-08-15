// # Copyright (c) Simon Parry.
// # See LICENSE for details.

#ifndef PROGRESSDIALOG_H
#define PROGRESSDIALOG_H

#include <QDialog>

class QAbstractButton;

namespace Ui {
    class ProgressDialog;
}

class ProgressDialog : public QDialog
{
    Q_OBJECT

public:
    explicit ProgressDialog(QWidget *parent = 0);
    ~ProgressDialog();

signals:
    void cancelled(const QString &id);

public slots:
    void updateProgress(int value);
    void setLabel(const QString &id);

private:
    Ui::ProgressDialog *ui;

private slots:
    void on_progressBar_valueChanged(int value);
    void on_pushButton_cancel_clicked();
};

#endif // PROGRESSDIALOG_H
