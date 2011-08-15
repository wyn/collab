// # Copyright (c) Simon Parry.
// # See LICENSE for details.

#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>

#include "QXmppClient.h"
#include <QDateTime>

class QAbstractButton;
class QXmppWrapper;
class ProgressDialog;

namespace Ui {
    class MainWindow;
}

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    explicit MainWindow(QWidget *parent = 0);
    ~MainWindow();

public slots:
    void onConnected();
    void onDisconnected();
    void onError(const QXmppClient::Error &err);

    void onStarted(const QString &id);
    void onCancelled(const QString &id);
    void onProgress(const QString &id, int progress);
    void onResult(const QString &id, const QMap<double, double> &percentiles);

private:
    Ui::MainWindow *ui;
    QXmppWrapper *xmppWrapper;
    QMap<QString, ProgressDialog*> progressDialogs;
    QMap<QString, QDateTime> startTimes;

private slots:
    void on_horizontalSlider_valueChanged(int value);
    void on_buttonBox_clicked(QAbstractButton* button);
    void on_toolButton_viewOutput_clicked();
    void on_toolButton_setOutput_clicked();
    void on_toolButton_viewInput_clicked();
    void on_toolButton_setInput_clicked();

    void onRegister_triggered();
    void onUnregister_triggered();
    void onRun_triggered();

private:
    enum Consts {
        default_number_runs = 10,
        run_factor = 1000
    };
};

#endif // MAINWINDOW_H
