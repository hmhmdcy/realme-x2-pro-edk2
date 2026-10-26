#version 450
layout(location=0) out vec4 color;
void main() {
    uint x = uint(gl_FragCoord.x), y = uint(gl_FragCoord.y);
    color = vec4(1, ((x / 32u + y / 32u) & 1u) != 0u ? 1 : 0, 0, 1);
}
