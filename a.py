import platform
import os
import sys
import numpy as np

PLATFORM    = platform.system()
IS_MACOS    = PLATFORM == "Darwin"
IS_LINUX    = PLATFORM == "Linux"
IS_WINDOWS  = PLATFORM == "Windows"
IS_SILICON  = IS_MACOS and (platform.machine() == "arm64")

print(f"[Platform] {PLATFORM} {'(Apple Silicon)' if IS_SILICON else ''}")

# ── Intento wgpu ─────────────────────────────────────────────────────────────
USE_WGPU = False
try:
    import wgpu
    import wgpu.backends.auto   # elige Metal en macOS, Vulkan en Linux/Win
    USE_WGPU = True
    print(f"[GPU] wgpu disponible → {'Metal nativo' if IS_MACOS else 'Vulkan/DX12'}")
except ImportError:
    print("[GPU] wgpu no instalado → pip install wgpu")
    print("[GPU] Usando OpenGL fallback")

# ── Parámetros ────────────────────────────────────────────────────────────────
SIZE        = 200
GENERATIONS = 500

history = np.random.randint(0, 2, (GENERATIONS, SIZE, SIZE))
pts_list = []
for g in range(GENERATIONS):
    x, y = np.where(history[g] == 1)
    z    = np.full_like(x, g)
    pts_list.append(np.column_stack((x, y, z)).astype(np.float32))

all_points = np.vstack(pts_list)
N = len(all_points)
print(f"[Sim] Generaciones: {GENERATIONS}, Células vivas: {N}")

# ── Matrices (column-major, convención OpenGL/WGSL) ──────────────────────────
CX = SIZE        / 2.0
CY = SIZE        / 2.0
CZ = GENERATIONS / 2.0

BASE_DIST = 50.0
ZOOM_MIN  = 5.0

def perspective(fov_deg, aspect, near, far):
    f = 1.0 / np.tan(np.radians(fov_deg) / 2)
    return np.array([
        [f/aspect, 0,  0,                         0                      ],
        [0,        f,  0,                         0                      ],
        [0,        0,  (far+near)/(near-far),     (2*far*near)/(near-far)],
        [0,        0,  -1,                        0                      ],
    ], dtype=np.float32)

def translate(tx, ty, tz):
    m = np.eye(4, dtype=np.float32)
    m[:3, 3] = [tx, ty, tz]
    return m

def rot_x_mat(deg):
    a = np.radians(deg); c, s = float(np.cos(a)), float(np.sin(a))
    return np.array([[1,0,0,0],[0,c,-s,0],[0,s,c,0],[0,0,0,1]], dtype=np.float32)

def rot_y_mat(deg):
    a = np.radians(deg); c, s = float(np.cos(a)), float(np.sin(a))
    return np.array([[c,0,s,0],[0,1,0,0],[-s,0,c,0],[0,0,0,1]], dtype=np.float32)

def compute_mvp(rx, ry, dist):
    proj  = perspective(45, 1000/800, 0.1, 1e9)
    view  = translate(0, 0, -dist) @ translate(-CX, -CY, -CZ)
    model = translate(CX,CY,CZ) @ rot_y_mat(ry) @ rot_x_mat(rx) @ translate(-CX,-CY,-CZ)
    return proj @ view @ model

# ── Geometría del cubo ────────────────────────────────────────────────────────
def make_cube_geometry():
    s = 0.48
    faces = np.array([
        [-s,-s, s],[ s,-s, s],[ s, s, s],  [-s,-s, s],[ s, s, s],[-s, s, s],
        [-s,-s,-s],[-s, s,-s],[ s, s,-s],  [-s,-s,-s],[ s, s,-s],[ s,-s,-s],
        [-s,-s,-s],[-s,-s, s],[-s, s, s],  [-s,-s,-s],[-s, s, s],[-s, s,-s],
        [ s,-s,-s],[ s, s,-s],[ s, s, s],  [ s,-s,-s],[ s, s, s],[ s,-s, s],
        [-s, s,-s],[-s, s, s],[ s, s, s],  [-s, s,-s],[ s, s, s],[ s, s,-s],
        [-s,-s,-s],[ s,-s,-s],[ s,-s, s],  [-s,-s,-s],[ s,-s, s],[-s,-s, s],
    ], dtype=np.float32)
    face_flags = np.zeros(len(faces), dtype=np.float32)
    edges = np.array([
        [-s,-s,-s],[ s,-s,-s], [ s,-s,-s],[ s, s,-s],
        [ s, s,-s],[-s, s,-s], [-s, s,-s],[-s,-s,-s],
        [-s,-s, s],[ s,-s, s], [ s,-s, s],[ s, s, s],
        [ s, s, s],[-s, s, s], [-s, s, s],[-s,-s, s],
        [-s,-s,-s],[-s,-s, s], [ s,-s,-s],[ s,-s, s],
        [ s, s,-s],[ s, s, s], [-s, s,-s],[-s, s, s],
    ], dtype=np.float32)
    edge_flags = np.ones(len(edges), dtype=np.float32)
    return faces, face_flags, edges, edge_flags


if USE_WGPU:
    import glfw
    import ctypes
    import Metal        # pyobjc-framework-Metal
    import Cocoa        # pyobjc-framework-Cocoa
    import objc
    from Foundation import NSAutoreleasePool

    # Shader MSL (Metal Shading Language)
    MSL_SHADER = """
#include <metal_stdlib>
using namespace metal;

struct Uniforms { float4x4 mvp; };

struct VertIn {
    float3 vert   [[attribute(0)]];
    float  edge   [[attribute(1)]];
    float3 offset [[attribute(2)]];
};

struct VertOut {
    float4 pos  [[position]];
    float  edge;
};

vertex VertOut vert_main(VertIn in [[stage_in]],
                         constant Uniforms &u [[buffer(2)]]) {
    VertOut out;
    out.pos  = u.mvp * float4(in.vert + in.offset, 1.0);
    out.edge = in.edge;
    return out;
}

fragment float4 frag_main(VertOut in [[stage_in]]) {
    return (in.edge > 0.5)
        ? float4(0, 1, 0, 1)   // aristas verdes
        : float4(1, 1, 1, 1);  // caras blancas
}
"""

    WIDTH, HEIGHT = 1000, 800

    # ── Init glfw ──────────────────────────────────────────────────────────
    if not glfw.init():
        raise RuntimeError("glfw.init() falló")
    glfw.window_hint(glfw.CLIENT_API, glfw.NO_API)   # sin OpenGL
    window = glfw.create_window(WIDTH, HEIGHT,
        f"Game of Life 3D [Metal {'Apple Silicon' if IS_SILICON else 'macOS'}]",
        None, None)
    if not window:
        glfw.terminate()
        raise RuntimeError("No se pudo crear la ventana glfw")

    # ── Obtener MTLDevice (GPU) ─────────────────────────────────────────────
    pool    = NSAutoreleasePool.alloc().init()
    devices = Metal.MTLCopyAllDevices()
    device  = devices[0]
    print(f"[Metal] GPU: {device.name()}")

    # ── CAMetalLayer (surface de presentación) ─────────────────────────────
    # Obtener NSWindow desde glfw y añadir una CAMetalLayer
    from ctypes import cdll, c_void_p
    glfw_lib  = cdll.LoadLibrary(glfw.get_cocoa_library_path() if hasattr(glfw, 'get_cocoa_library_path') else 'libglfw.3.dylib')
    ns_window = c_void_p(glfw.get_cocoa_window(window))

    layer = Metal.CAMetalLayer.layer()
    layer.setDevice_(device)
    pixel_fmt = Metal.MTLPixelFormatBGRA8Unorm
    layer.setPixelFormat_(pixel_fmt)
    layer.setFramebufferOnly_(True)

    # Asociar la layer a la ventana vía ObjC runtime
    ns_view = objc.objc_object(c_void_p=ns_window.value)
    try:
        content_view = ns_view.contentView()
        content_view.setLayer_(layer)
        content_view.setWantsLayer_(True)
    except Exception as e:
        print(f"[Metal] Advertencia al configurar layer: {e}")

    # ── Compilar shaders ───────────────────────────────────────────────────
    err    = objc.nil
    lib, err = device.newLibraryWithSource_options_error_(MSL_SHADER, None, None)
    if lib is None:
        raise RuntimeError(f"Error compilando shaders MSL: {err}")
    vert_fn = lib.newFunctionWithName_("vert_main")
    frag_fn = lib.newFunctionWithName_("frag_main")
    print("[Metal] Shaders MSL compilados OK")

    # ── Vertex descriptor ──────────────────────────────────────────────────
    # pyobjc: usar objectAtIndexedSubscript_ en lugar de [] y set* en lugar de *_
    vdesc = Metal.MTLVertexDescriptor.vertexDescriptor()
    a = vdesc.attributes().objectAtIndexedSubscript_
    l = vdesc.layouts().objectAtIndexedSubscript_

    # attr 0: vert  (float3, offset 0,  buffer 0, per-vertex)
    a(0).setFormat_(Metal.MTLVertexFormatFloat3)
    a(0).setOffset_(0)
    a(0).setBufferIndex_(0)
    # attr 1: edge  (float,  offset 12, buffer 0, per-vertex)
    a(1).setFormat_(Metal.MTLVertexFormatFloat)
    a(1).setOffset_(12)
    a(1).setBufferIndex_(0)
    # attr 2: offset (float3, offset 0, buffer 1, per-instance)
    a(2).setFormat_(Metal.MTLVertexFormatFloat3)
    a(2).setOffset_(0)
    a(2).setBufferIndex_(1)
    # layouts
    l(0).setStride_(16)
    l(0).setStepFunction_(Metal.MTLVertexStepFunctionPerVertex)
    l(1).setStride_(12)
    l(1).setStepFunction_(Metal.MTLVertexStepFunctionPerInstance)
    # ── Depth stencil ──────────────────────────────────────────────────────
    depth_fmt  = Metal.MTLPixelFormatDepth32Float
    ds_desc    = Metal.MTLDepthStencilDescriptor.alloc().init()
    ds_desc.setDepthCompareFunction_(Metal.MTLCompareFunctionLess)
    ds_desc.setDepthWriteEnabled_(True)
    depth_state = device.newDepthStencilStateWithDescriptor_(ds_desc)

    depth_tex = None
    def make_depth_tex(w, h):
        td = Metal.MTLTextureDescriptor.texture2DDescriptorWithPixelFormat_width_height_mipmapped_(
            depth_fmt, w, h, False)
        td.setUsage_(Metal.MTLTextureUsageRenderTarget)
        td.setStorageMode_(Metal.MTLStorageModePrivate)
        return device.newTextureWithDescriptor_(td)
    depth_tex = make_depth_tex(WIDTH, HEIGHT)

    # ── Render pipeline ────────────────────────────────────────────────────
    def make_pipeline(primitive_topology=None):
        pd = Metal.MTLRenderPipelineDescriptor.alloc().init()
        pd.setVertexFunction_(vert_fn)
        pd.setFragmentFunction_(frag_fn)
        pd.setVertexDescriptor_(vdesc)
        pd.colorAttachments().objectAtIndexedSubscript_(0).setPixelFormat_(pixel_fmt)
        pd.setDepthAttachmentPixelFormat_(depth_fmt)
        pipe, err = device.newRenderPipelineStateWithDescriptor_error_(pd, None)
        if pipe is None:
            raise RuntimeError(f"Pipeline error: {err}")
        return pipe

    pipeline = make_pipeline()
    cmd_queue = device.newCommandQueue()

    # ── Geometría ──────────────────────────────────────────────────────────
    faces, face_flags, edges, edge_flags = make_cube_geometry()

    def interleave(verts, flags):
        return np.column_stack([verts, flags]).astype(np.float32)

    face_data  = interleave(faces, face_flags)
    edge_data  = interleave(edges, edge_flags)

    def make_buf(data):
        arr = np.ascontiguousarray(data, dtype=np.float32)
        return device.newBufferWithBytes_length_options_(
            arr.tobytes(), arr.nbytes, Metal.MTLResourceStorageModeShared)

    vbuf_faces   = make_buf(face_data)
    vbuf_edges   = make_buf(edge_data)
    offsets_buf  = make_buf(all_points)
    # uniform_buf se crea cada frame con newBufferWithBytes_length_options_

    n_fv = len(face_data)
    n_ev = len(edge_data)

    # ── Estado mutable ─────────────────────────────────────────────────────
    S = {"rx": 0.0, "ry": 0.0, "dist": BASE_DIST,
         "last_scroll_y": 0.0, "w": WIDTH, "h": HEIGHT}

    def scroll_cb(win, dx, dy):
        speed = max(1.0, S["dist"] * 0.05)
        S["dist"] = max(ZOOM_MIN, S["dist"] - dy * speed)

    glfw.set_scroll_callback(window, scroll_cb)

    print(f"[Metal] Renderizando {N} instancias | Controles: flechas=rotar  scroll=zoom  R=reset")

    while not glfw.window_should_close(window):
        glfw.poll_events()

        # Teclado
        def key(k): return glfw.get_key(window, k) == glfw.PRESS
        if key(glfw.KEY_LEFT):  S["ry"] -= 1
        if key(glfw.KEY_RIGHT): S["ry"] += 1
        if key(glfw.KEY_UP):    S["rx"] -= 1
        if key(glfw.KEY_DOWN):  S["rx"] += 1
        if key(glfw.KEY_EQUAL) or key(glfw.KEY_KP_ADD):
            S["dist"] = max(ZOOM_MIN, S["dist"] - max(1.0, S["dist"] * 0.02))
        if key(glfw.KEY_MINUS) or key(glfw.KEY_KP_SUBTRACT):
            S["dist"] += max(1.0, S["dist"] * 0.02)
        if key(glfw.KEY_R):
            S["rx"] = S["ry"] = 0.0; S["dist"] = BASE_DIST

        # MVP → uniform buffer
        mvp = compute_mvp(S["rx"], S["ry"], S["dist"])
        mvp_bytes = mvp.T.astype(np.float32).tobytes()
        # Crear buffer de uniforms con los bytes directamente (más simple y confiable)
        uniform_buf = device.newBufferWithBytes_length_options_(
            mvp_bytes, 64, Metal.MTLResourceStorageModeShared)

        # Obtener drawable de la CAMetalLayer
        drawable = layer.nextDrawable()
        if drawable is None:
            continue

        # Resize depth si cambia el tamaño
        fw, fh = glfw.get_framebuffer_size(window)
        if (fw, fh) != (S["w"], S["h"]):
            depth_tex = make_depth_tex(fw, fh)
            layer.setDrawableSize_((fw, fh))
            S["w"], S["h"] = fw, fh

        # Render pass descriptor
        rpd = Metal.MTLRenderPassDescriptor.renderPassDescriptor()
        rpd.colorAttachments().objectAtIndexedSubscript_(0).setTexture_(drawable.texture())
        rpd.colorAttachments().objectAtIndexedSubscript_(0).setLoadAction_(Metal.MTLLoadActionClear)
        rpd.colorAttachments().objectAtIndexedSubscript_(0).setClearColor_(Metal.MTLClearColorMake(0.05, 0.05, 0.1, 1.0))
        rpd.colorAttachments().objectAtIndexedSubscript_(0).setStoreAction_(Metal.MTLStoreActionStore)
        rpd.depthAttachment().setTexture_(depth_tex)
        rpd.depthAttachment().setLoadAction_(Metal.MTLLoadActionClear)
        rpd.depthAttachment().setClearDepth_(1.0)
        rpd.depthAttachment().setStoreAction_(Metal.MTLStoreActionDontCare)

        cmd_buf = cmd_queue.commandBuffer()
        enc     = cmd_buf.renderCommandEncoderWithDescriptor_(rpd)

        enc.setRenderPipelineState_(pipeline)
        enc.setDepthStencilState_(depth_state)
        enc.setVertexBuffer_offset_atIndex_(uniform_buf, 0, 2)  # uniforms en buffer(2)

        # Caras
        enc.setVertexBuffer_offset_atIndex_(vbuf_faces, 0, 0)
        enc.setVertexBuffer_offset_atIndex_(offsets_buf, 0, 1)
        enc.drawPrimitives_vertexStart_vertexCount_instanceCount_(
            Metal.MTLPrimitiveTypeTriangle, 0, n_fv, N)

        # Aristas
        enc.setVertexBuffer_offset_atIndex_(vbuf_edges, 0, 0)
        enc.setVertexBuffer_offset_atIndex_(offsets_buf, 0, 1)
        enc.drawPrimitives_vertexStart_vertexCount_instanceCount_(
            Metal.MTLPrimitiveTypeLine, 0, n_ev, N)

        enc.endEncoding()
        cmd_buf.presentDrawable_(drawable)
        cmd_buf.commit()

    glfw.destroy_window(window)
    glfw.terminate()
    del pool

else:
    import pygame
    from pygame.locals import DOUBLEBUF, OPENGL
    from OpenGL.GL import (
        GL_VERSION, GL_DEPTH_TEST,
        GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT,
        GL_ARRAY_BUFFER, GL_STATIC_DRAW,
        GL_FLOAT, GL_FALSE, GL_TRIANGLES, GL_LINES,
        glGetString, glEnable, glViewport,
        glClearColor, glClear, glUseProgram,
        glGenVertexArrays, glBindVertexArray,
        glGenBuffers, glBindBuffer, glBufferData,
        glEnableVertexAttribArray,
        glVertexAttribPointer, glVertexAttribDivisor,
        glDrawArraysInstanced,
        glGetUniformLocation, glUniformMatrix4fv,
        GL_VERTEX_SHADER, GL_FRAGMENT_SHADER, GL_COMPILE_STATUS, GL_LINK_STATUS,
        glCreateShader, glShaderSource, glCompileShader,
        glGetShaderiv, glGetShaderInfoLog, glDeleteShader,
        glCreateProgram, glAttachShader, glLinkProgram,
        glGetProgramiv, glGetProgramInfoLog,
    )

    VERT_GLSL = """
#version 410 core
layout(location=0) in vec3  in_vert;
layout(location=1) in float in_edge;
layout(location=2) in vec3  in_offset;
uniform mat4 mvp;
out float v_edge;
void main() {
    gl_Position = mvp * vec4(in_vert + in_offset, 1.0);
    v_edge = in_edge;
}
"""
    FRAG_GLSL = """
#version 410 core
in  float v_edge;
out vec4  fragColor;
void main() {
    fragColor = (v_edge > 0.5)
        ? vec4(0.0,1.0,0.0,1.0)
        : vec4(1.0,1.0,1.0,1.0);
}
"""

    def compile_shader(src, kind):
        sh = glCreateShader(kind)
        glShaderSource(sh, src)
        glCompileShader(sh)
        if not glGetShaderiv(sh, GL_COMPILE_STATUS):
            raise RuntimeError(glGetShaderInfoLog(sh).decode())
        return sh

    def link_prog(vs_src, fs_src):
        vs = compile_shader(vs_src, GL_VERTEX_SHADER)
        fs = compile_shader(fs_src, GL_FRAGMENT_SHADER)
        p  = glCreateProgram()
        glAttachShader(p, vs); glAttachShader(p, fs)
        glLinkProgram(p)
        glDeleteShader(vs); glDeleteShader(fs)
        if not glGetProgramiv(p, GL_LINK_STATUS):
            raise RuntimeError(glGetProgramInfoLog(p).decode())
        return p

    pygame.init()
    display = (1000, 800)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 4)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 1)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK,
                                    pygame.GL_CONTEXT_PROFILE_CORE)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_FORWARD_COMPATIBLE_FLAG, True)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Game of Life 3D [OpenGL fallback]  |  Rueda: zoom  |  Flechas: rotar  |  R: reset")

    print(f"[OpenGL] {glGetString(GL_VERSION).decode()}")
    glViewport(0, 0, *display)

    prog    = link_prog(VERT_GLSL, FRAG_GLSL)
    glUseProgram(prog)
    mvp_loc = glGetUniformLocation(prog, "mvp")

    faces, face_flags, edges, edge_flags = make_cube_geometry()

    def build_vao(verts, flags):
        vao = glGenVertexArrays(1)
        glBindVertexArray(vao)
        for loc, data, n_comp, divisor in [
            (0, verts,       3, 0),
            (1, flags[:,None] if flags.ndim==1 else flags, 1, 0),
            (2, all_points,  3, 1),
        ]:
            vbo = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, vbo)
            d = data if data.ndim == 2 else data.reshape(-1, n_comp)
            flat = d.astype(np.float32)
            glBufferData(GL_ARRAY_BUFFER, flat.nbytes, flat, GL_STATIC_DRAW)
            glEnableVertexAttribArray(loc)
            glVertexAttribPointer(loc, n_comp, GL_FLOAT, GL_FALSE, 0, None)
            glVertexAttribDivisor(loc, divisor)
        glBindVertexArray(0)
        return vao, len(verts)

    vao_f, n_fv = build_vao(faces, face_flags)
    vao_e, n_ev = build_vao(edges, edge_flags)

    glEnable(GL_DEPTH_TEST)
    rx = ry = 0.0
    dist  = BASE_DIST
    clock = pygame.time.Clock()
    running = True

    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.MOUSEWHEEL:
                speed = max(1.0, dist * 0.05)
                dist -= e.y * speed
                dist  = max(ZOOM_MIN, dist)
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_r:
                    rx = ry = 0.0; dist = BASE_DIST

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:  ry -= 1
        if keys[pygame.K_RIGHT]: ry += 1
        if keys[pygame.K_UP]:    rx -= 1
        if keys[pygame.K_DOWN]:  rx += 1
        if keys[pygame.K_EQUALS] or keys[pygame.K_PLUS]:
            dist = max(ZOOM_MIN, dist - max(1.0, dist * 0.02))
        if keys[pygame.K_MINUS]:
            dist += max(1.0, dist * 0.02)

        mvp = compute_mvp(rx, ry, dist)
        glClearColor(0.05, 0.05, 0.1, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glUseProgram(prog)
        glUniformMatrix4fv(mvp_loc, 1, GL_FALSE, mvp.T)

        glBindVertexArray(vao_f)
        glDrawArraysInstanced(GL_TRIANGLES, 0, n_fv, N)
        glBindVertexArray(vao_e)
        glDrawArraysInstanced(GL_LINES, 0, n_ev, N)
        glBindVertexArray(0)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()