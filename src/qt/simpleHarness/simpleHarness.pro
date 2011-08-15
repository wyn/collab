# Copyright (c) Simon Parry.
# See LICENSE for details.

#-------------------------------------------------
#
# Project created by QtCreator 2011-08-01T09:52:30
#
#-------------------------------------------------

QT += core gui
# for QXMPP support
QT += network xml

TARGET = simpleHarness
TEMPLATE = app

SOURCES += main.cpp\
        MainWindow.cpp \
    ProgressDialog.cpp \
    RegisterDialog.cpp \
    QXmppWrapper.cpp

HEADERS  += MainWindow.h \
    ProgressDialog.h \
    RegisterDialog.h \
    QXmppWrapper.h

FORMS    += MainWindow.ui \
    ProgressDialog.ui \
    RegisterDialog.ui


# QXMPP library files and headers
INCLUDEPATH += /include/qxmpp
LIBS += -L/Library/Frameworks
LIBS += -lqxmpp
