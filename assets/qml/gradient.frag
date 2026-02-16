#version 440

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float iTime;
    vec4 bgColor;
    vec4 color1;
    vec4 color2;
};

float hash12(vec2 p) {
    vec3 p3 = fract(vec3(p.xyx) * 0.1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
}

vec3 toLinear(vec3 c) {
    return pow(c, vec3(2.2));
}

vec3 toSrgb(vec3 c) {
    return pow(max(c, vec3(0.0)), vec3(1.0 / 2.2));
}

void main() {
    vec2 uv = qt_TexCoord0;
    vec2 center = vec2(0.5);

    // Slowly rotating angle
    float angle = iTime * 0.21;
    float c = cos(angle);
    float s = sin(angle);

    // Project UV onto the rotating axis (result in -0.7 .. +0.7)
    vec2 d = uv - center;
    float t = dot(d, vec2(c, s)) + 0.5;

    // Blend in linear color space to reduce visible stepping.
    vec3 colLin = toLinear(bgColor.rgb);
    colLin = mix(colLin, toLinear(color1.rgb), smoothstep(0.15, 0.40, t) * 0.19);
    colLin = mix(colLin, toLinear(color2.rgb), smoothstep(0.60, 0.85, t) * 0.19);
    vec3 col = toSrgb(colLin);

    // Two-phase temporal dithering further hides 8-bit quantization.
    float n0 = hash12(gl_FragCoord.xy + vec2(iTime * 11.7, iTime * 7.3)) - 0.5;
    float n1 = hash12(gl_FragCoord.yx + vec2(-iTime * 5.2, iTime * 9.1)) - 0.5;
    float n = n0 + n1;
    col = clamp(col + (n * (1.6 / 255.0)), 0.0, 1.0);

    fragColor = vec4(col, 1.0) * qt_Opacity;
}
