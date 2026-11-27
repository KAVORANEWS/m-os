/* M OS installer slideshow. SPDX-License-Identifier: GPL-3.0-or-later */
import QtQuick 2.0;
import calamares.slideshow 1.0;

Presentation
{
    id: presentation

    function nextSlide() { presentation.goToNextSlide(); }

    Timer {
        id: advanceTimer
        interval: 8000
        running: presentation.activatedInCalamares
        repeat: true
        onTriggered: nextSlide()
    }

    function onActivate() { }
    function onLeave() { }

    Slide {
        Image { anchors.fill: parent; source: "slide-bg.png"; fillMode: Image.PreserveAspectCrop }
        Column {
            anchors.centerIn: parent; spacing: 16
            Image { anchors.horizontalCenter: parent.horizontalCenter; source: "logo.png"; width: 96; height: 96 }
            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Welcome to M OS"; color: "white"; font.pixelSize: 30; font.bold: true }
            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Your Computer. Your Experience. Your OS."; color: "#C7D2FE"; font.pixelSize: 16 }
        }
    }
    Slide {
        Image { anchors.fill: parent; source: "slide-bg.png"; fillMode: Image.PreserveAspectCrop }
        Column {
            anchors.centerIn: parent; spacing: 12; width: parent.width * 0.75
            Text { text: "Two desktop layouts"; color: "white"; font.pixelSize: 26; font.bold: true }
            Text { width: parent.width; wrapMode: Text.WordWrap; color: "#E0E7FF"; font.pixelSize: 16
                   text: "Choose M OS Modern (top bar and dock) or M OS Classic (taskbar and start menu) in M OS Welcome or the Control Center — switch any time." }
        }
    }
    Slide {
        Image { anchors.fill: parent; source: "slide-bg.png"; fillMode: Image.PreserveAspectCrop }
        Column {
            anchors.centerIn: parent; spacing: 12; width: parent.width * 0.75
            Text { text: "Secure by default"; color: "white"; font.pixelSize: 26; font.bold: true }
            Text { width: parent.width; wrapMode: Text.WordWrap; color: "#E0E7FF"; font.pixelSize: 16
                   text: "Firewall enabled, AppArmor confinement, signed Debian packages and security updates through the M OS Update Center. No telemetry." }
        }
    }
    Slide {
        Image { anchors.fill: parent; source: "slide-bg.png"; fillMode: Image.PreserveAspectCrop }
        Column {
            anchors.centerIn: parent; spacing: 12; width: parent.width * 0.75
            Text { text: "සිංහල සහාය"; color: "white"; font.pixelSize: 26; font.bold: true }
            Text { width: parent.width; wrapMode: Text.WordWrap; color: "#E0E7FF"; font.pixelSize: 16
                   text: "Sinhala fonts and input methods (Wijesekara, Singlish) are included. Press Ctrl+Space to switch keyboard input." }
        }
    }
}
