#version 440

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float iTime;
    vec4 bgColor;
};

#define PI 3.1415926535897932384626433832795

const float wave_amplitude = 0.076;
const float period = 2.0 * PI;

float wave_phase() {
    return iTime;
}

float square(vec2 st) {
    vec2 bl = step(vec2(0.0), st);
    vec2 tr = step(vec2(0.0), 1.0 - st);
    return bl.x * bl.y * tr.x * tr.y;
}

vec4 frame(vec2 st) {
    float tushka = square(st * mat2(1.0 / 0.48, 0.0, 0.0, 1.0 / 0.69));

    mat2 sector_mat = mat2(1.0 / 0.16, 0.0, 0.0, 1.0 / 0.22);
    float sectors[4];
    sectors[0] = square(st * sector_mat + (1.0 / 0.16) * vec2(0.000, -0.280));
    sectors[1] = square(st * sector_mat + (1.0 / 0.16) * vec2(0.000, -0.060));
    sectors[2] = square(st * sector_mat + (1.0 / 0.16) * vec2(-0.240, -0.280));
    sectors[3] = square(st * sector_mat + (1.0 / 0.16) * vec2(-0.240, -0.060));
    vec3 sector_colors[4];
    sector_colors[0] = vec3(0.941, 0.439, 0.404) * sectors[0];
    sector_colors[1] = vec3(0.435, 0.682, 0.843) * sectors[1];
    sector_colors[2] = vec3(0.659, 0.808, 0.506) * sectors[2];
    sector_colors[3] = vec3(0.996, 0.859, 0.114) * sectors[3];

    return vec4(sector_colors[0] + sector_colors[1] +
                sector_colors[2] + sector_colors[3], tushka);
}

vec4 trail_piece(vec2 st, vec2 index, float scale) {
    scale = index.x * 0.082 + 0.452;

    vec3 color;
    if (index.y > 0.9 && index.y < 2.1) {
        color = vec3(0.435, 0.682, 0.843);
        scale *= 0.8;
    } else if (index.y > 3.9 && index.y < 5.1) {
        color = vec3(0.941, 0.439, 0.404);
        scale *= 0.8;
    } else {
        color = vec3(0.0, 0.0, 0.0);
    }

    float scale1 = 1.0 / scale;
    float shift = -(1.0 - scale) / (2.0 * scale);
    vec2 st2 = vec2(vec3(st, 1.0) * mat3(scale1, 0.0, shift, 0.0, scale1, shift, 0.0, 0.0, 1.0));
    float mask = square(st2);

    return vec4(color, mask);
}

vec4 trail(vec2 st) {
    const float piece_height = 7.0 / 0.69;
    const float piece_width = 6.0 / 0.54;

    st.x = 1.2760 * pow(st.x, 3.0) - 1.4624 * st.x * st.x + 1.4154 * st.x;

    float x_at_cell = floor(st.x * piece_width) / piece_width;
    float x_at_cell_center = x_at_cell + 0.016;
    float incline = cos(0.5 * period + wave_phase()) * wave_amplitude;

    float offset = sin(x_at_cell_center * period + wave_phase()) * wave_amplitude +
        incline * (st.x - x_at_cell) * 5.452;

    float mask = step(offset, st.y) * (1.0 - step(0.69 + offset, st.y)) * step(0.0, st.x);

    vec2 cell_coord = vec2((st.x - x_at_cell) * piece_width,
                           fract((st.y - offset) * piece_height));
    vec2 cell_index = vec2(x_at_cell * piece_width,
                           floor((st.y - offset) * piece_height));

    vec4 pieces = trail_piece(cell_coord, cell_index, 0.752);

    return vec4(vec3(pieces), pieces.a * mask);
}

vec4 logo(vec2 st) {
    if (st.x <= 0.54) {
        return trail(st);
    } else {
        vec2 st2 = st + vec2(0.0, -sin(st.x * period + wave_phase()) * wave_amplitude);
        return frame(st2 + vec2(-0.54, 0.0));
    }
}

void main() {
    vec2 st = qt_TexCoord0;
    float aspect = 1.7778;
    st.x *= aspect;

    st *= 1.472;
    st += vec2(-0.7, -0.68);
    float rot = PI * -0.124;
    st *= mat2(cos(rot), sin(rot), -sin(rot), cos(rot));

    vec4 logo_ = logo(st);
    vec4 teal = vec4(0.0, 0.5, 0.5, 1.0);
    fragColor = mix(mix(vec4(bgColor.rgb, 1.0), teal, 0.5), logo_, logo_.a) * qt_Opacity;
}
