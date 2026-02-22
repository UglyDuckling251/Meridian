import QtQuick
import QtQuick.Shapes

/*
 *  GPU-rendered background for Meridian.
 *
 *  Waves use compiled GLSL fragment shaders (.qsb) via
 *  ShaderEffect — all maths run on the GPU in 32-bit float, so there
 *  is zero 8-bit colour banding.
 *
 *  Starscape uses QML scene-graph primitives (Rectangle items)
 *  which are also composited by the GPU at native precision.
 */

Item {
    id: root

    // ---- Properties set from Python ---------------------------------
    property string mode:          "None"
    property color  bgBase:        "#0E1218"
    property color  accent1:       "#5DADE2"
    property color  accent2:       "#48C9B0"
    property string imagePath:     ""
    property string animType:      ""
    property bool   reducedMotion: false
    property real   fps:           30

    // ---- Internal animation clock -----------------------------------
    property real elapsed: 0

    Timer {
        interval: Math.max(16, Math.round(1000 / root.fps))
        running:  root.mode === "Animation" && root.animType !== ""
                  && !root.reducedMotion
        repeat:   true
        onTriggered: root.elapsed += interval / 1000.0
    }

    // ================================================================
    //  Base fill
    // ================================================================
    Rectangle {
        anchors.fill: parent
        color: root.bgBase
    }

    // ================================================================
    //  Image mode
    // ================================================================
    Image {
        visible:  root.mode === "Image" && root.imagePath !== ""
        anchors.fill: parent
        source:   root.imagePath !== ""
                  ? "file:///" + root.imagePath : ""
        fillMode: Image.PreserveAspectCrop
        smooth:   true
        mipmap:   true
    }

    // ================================================================
    //  Animation: Waves  (GLSL shader)
    // ================================================================
    ShaderEffect {
        visible:      root.mode === "Animation" && root.animType === "waves"
        anchors.fill: parent

        property real  iTime:   root.elapsed
        property color bgColor: root.bgBase
        property color color1:  root.accent1
        property color color2:  root.accent2

        fragmentShader: "waves.frag.qsb"
    }

    // ================================================================
    //  Animation: 1998  (Windows 98 flag GLSL shader)
    // ================================================================
    ShaderEffect {
        visible:      root.mode === "Animation" && root.animType === "1998"
        anchors.fill: parent

        property real  iTime:   root.elapsed
        property color bgColor: root.bgBase

        fragmentShader: "flag1998.frag.qsb"
    }

    // ================================================================
    //  Animation: Starscape  (scene-graph dots — GPU composited)
    // ================================================================
    Item {
        id: starfield
        visible: root.mode === "Animation" && root.animType === "starscape"
        anchors.fill: parent
        layer.enabled: true
        layer.smooth: true
        layer.samples: 8

        property var stars: []

        Component.onCompleted: {
            var list = [];
            for (var i = 0; i < 70; i++) {
                var seed = i * 67.3;
                list.push({
                    angle:  seed * 0.1,
                    speed:  12 + (i % 10) * 6,
                    seed:   seed,
                    twRate: 2.0 + (i % 5) * 0.7,
                    colBucket: i % 5 === 0 ? 0 : (i % 7 === 0 ? 1 : 2)
                });
            }
            stars = list;
        }

        Repeater {
            model: starfield.stars
            Rectangle {
                property real maxDist: Math.max(root.width, root.height) * 0.8
                property real dist: (root.elapsed * modelData.speed
                                     + modelData.seed) % maxDist
                property real sx: root.width  / 2
                                  + Math.cos(modelData.angle) * dist
                property real sy: root.height / 2
                                  + Math.sin(modelData.angle) * dist
                property real twinkle: 0.5 + 0.5 * Math.sin(
                    root.elapsed * modelData.twRate + modelData.seed)
                property real al: 0.06 + 0.22 * twinkle
                                  * Math.min(1.0, dist * 0.005)
                property real sz: 1.0 + dist * 0.004 + twinkle * 0.8

                visible: sx >= 0 && sx <= root.width
                         && sy >= 0 && sy <= root.height
                x: sx - sz / 2;  y: sy - sz / 2
                width: sz;       height: sz
                radius: sz / 2
                antialiasing: true
                color: {
                    var c = modelData.colBucket === 0 ? root.accent1
                          : modelData.colBucket === 1 ? root.accent2
                          : Qt.rgba(
                              Math.min(1, root.bgBase.r + 0.6),
                              Math.min(1, root.bgBase.g + 0.6),
                              Math.min(1, root.bgBase.b + 0.6), 1);
                    return Qt.rgba(c.r, c.g, c.b, al);
                }
            }
        }
    }
}
