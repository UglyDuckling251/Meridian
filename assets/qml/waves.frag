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

float wave(vec2 uv, float inv_size, float period, float inv_amplitude,
           float x_offset, float y_offset, float flip, float speed) {
    float wv = ((uv.y - y_offset) * inv_size)
             - (sin(((x_offset + uv.x) / period) + (speed * iTime)) / inv_amplitude);
    wv *= step(abs(wv), 0.4) * flip;
    return wv;
}

void main() {
    vec2 uv = qt_TexCoord0;

    // Base colour from theme with a very subtle diagonal lift
    vec3 col = bgColor.rgb + vec3((uv.x + uv.y) * 0.02);

    // Primary wave group (accent colour 1)
    col += color1.rgb * clamp(wave(uv, 4.0, 1.0,  3.0, 0.0, 0.4,  1.0, -0.10), 0.0, 0.4);
    col += color1.rgb * clamp(wave(uv, 4.0, 0.4,  1.0, 0.0, 0.5,  1.0,  0.10), 0.0, 0.4);

    // Secondary wave group (accent colour 2)
    col += color2.rgb * clamp(wave(uv, 4.0, 0.2,  6.0, 3.0, 0.3, -1.0,  0.13), 0.0, 0.4);
    col += color2.rgb * clamp(wave(uv, 4.0, 0.15, 7.0, 4.0, 0.4, -1.0, -0.18), 0.0, 0.4);

    // Subtle dithering to avoid low-contrast banding in darker themes.
    float n = (hash12(gl_FragCoord.xy + vec2(iTime * 3.7, iTime * 2.1)) - 0.5) * 2.0;
    col = clamp(col + (n * (0.8 / 255.0)), 0.0, 1.0);

    fragColor = vec4(col, 1.0) * qt_Opacity;
}
