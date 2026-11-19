// Minimal slangc: compile one entry point of a .slang file to SPIR-V 1.5 (entry renamed "main",
// column-major matrices), the way Astra Novum's shaders are built.
// usage: slangc <file.slang> <entryPoint> <out.spv> [search dir]
#include <cstddef>
#include "slang.h"
namespace Slang {
template <class T> struct ComPtr {
    T* p = nullptr;
    ~ComPtr() { if (p) p->release(); }
    T** writeRef() { if (p) { p->release(); p = nullptr; } return &p; }
    T* operator->() const { return p; }
    operator T*() const { return p; }
    ComPtr& operator=(std::nullptr_t) { if (p) p->release(); p = nullptr; return *this; }
};
}
#include <cstdio>
#include <cstddef>
#include <string>
#include <fstream>
using namespace slang;
static void diag(ISlangBlob* d) { if (d && d->getBufferSize()) fprintf(stderr, "%s\n", (const char*)d->getBufferPointer()); }
int main(int argc, char** argv)
{
    if (argc < 4) { fprintf(stderr, "usage: slangc file.slang entry out.spv [searchdir]\n"); return 2; }
    std::string file = argv[1], entry = argv[2], out = argv[3];
    std::string dir = argc > 4 ? argv[4] : file.substr(0, file.find_last_of('/') == std::string::npos ? 0 : file.find_last_of('/'));
    if (dir.empty()) dir = ".";
    Slang::ComPtr<IGlobalSession> gs;
    if (SLANG_FAILED(slang_createGlobalSession(SLANG_API_VERSION, gs.writeRef()))) { fprintf(stderr, "no global session\n"); return 1; }
    TargetDesc t = {};
    t.format = SLANG_SPIRV;
    t.profile = gs->findProfile("spirv_1_5");
    CompilerOptionEntry opts[1];
    opts[0].name = CompilerOptionName::MatrixLayoutColumn;
    opts[0].value.kind = CompilerOptionValueKind::Int;
    opts[0].value.intValue0 = 1;
    const char* paths[] = { dir.c_str() };
    SessionDesc sd = {};
    sd.targets = &t; sd.targetCount = 1;
    sd.searchPaths = paths; sd.searchPathCount = 1;
    sd.compilerOptionEntries = opts; sd.compilerOptionEntryCount = 1;
    sd.defaultMatrixLayoutMode = SLANG_MATRIX_LAYOUT_COLUMN_MAJOR;
    Slang::ComPtr<ISession> s;
    if (SLANG_FAILED(gs->createSession(sd, s.writeRef()))) { fprintf(stderr, "no session\n"); return 1; }
    Slang::ComPtr<ISlangBlob> d;
    std::string mod = file.substr(file.find_last_of('/') + 1);
    mod = mod.substr(0, mod.rfind('.'));
    IModule* m = s->loadModule(mod.c_str(), d.writeRef()); diag(d);
    if (!m) return 1;
    Slang::ComPtr<IEntryPoint> ep;
    if (SLANG_FAILED(m->findEntryPointByName(entry.c_str(), ep.writeRef()))) { fprintf(stderr, "entry %s not found\n", entry.c_str()); return 1; }
    IComponentType* parts[] = { m, ep };
    Slang::ComPtr<IComponentType> comp, linked;
    d = nullptr;
    if (SLANG_FAILED(s->createCompositeComponentType(parts, 2, comp.writeRef(), d.writeRef()))) { diag(d); return 1; }
    d = nullptr;
    if (SLANG_FAILED(comp->link(linked.writeRef(), d.writeRef()))) { diag(d); return 1; }
    Slang::ComPtr<ISlangBlob> code; d = nullptr;
    if (SLANG_FAILED(linked->getEntryPointCode(0, 0, code.writeRef(), d.writeRef()))) { diag(d); return 1; }
    diag(d);
    std::ofstream(out, std::ios::binary).write((const char*)code->getBufferPointer(), code->getBufferSize());
    printf("%s: %zu bytes\n", out.c_str(), code->getBufferSize());
    return 0;
}
