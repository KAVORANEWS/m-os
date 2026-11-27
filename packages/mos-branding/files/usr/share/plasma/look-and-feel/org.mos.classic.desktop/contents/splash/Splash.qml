// M OS Plasma splash screen. SPDX-License-Identifier: LGPL-2.0-or-later
import QtQuick

Rectangle {
    id: root
    color: "#0B1020"
    property int stage

    onStageChanged: {
        if (stage === 2) { introAnimation.running = true }
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#11143A" }
            GradientStop { position: 1.0; color: "#070A18" }
        }
    }

    Column {
        id: content
        anchors.centerIn: parent
        spacing: 22
        opacity: 0

        Image {
            anchors.horizontalCenter: parent.horizontalCenter
            source: "images/mos-logo.svg"
            sourceSize.width: 112
            sourceSize.height: 112
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "M OS"
            color: "#FFFFFF"
            font.pixelSize: 34
            font.weight: Font.DemiBold
        }
        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 180; height: 4; radius: 2
            color: "#26294A"
            Rectangle {
                width: parent.width * Math.min(1, root.stage / 6)
                height: parent.height; radius: 2
                color: "#8B7CF8"
                Behavior on width { NumberAnimation { duration: 400; easing.type: Easing.OutCubic } }
            }
        }
    }

    OpacityAnimator {
        id: introAnimation
        target: content
        from: 0; to: 1
        duration: 600
        easing.type: Easing.InOutQuad
        running: false
    }
}
