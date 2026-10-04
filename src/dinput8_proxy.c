/*
 * dao-gamepad: dinput8.dll proxy for Dragon Age: Origins (Steam, buildid 21245176).
 *
 * Stage 0 (log only): forwards DirectInput8Create to the system dinput8.dll and, on the
 * first call, verifies the running build and wraps InputManager::Update (vtable slot 1).
 * The wrapper only calls the original and logs; it changes no game behaviour.
 *
 * The game calls DirectInput8Create from the InputManager constructor (FUN_0087f890), so
 * by then SteamStub has decrypted .text and the vtable at 0xb2ed28 is in use.
 */
#include <windows.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#include "dao_build.h"

typedef HRESULT(WINAPI *DirectInput8CreateFn)(HINSTANCE, DWORD, REFIID, LPVOID *, LPUNKNOWN);
typedef void(__attribute__((thiscall)) *InputUpdateFn)(void *self, void *arg);

typedef struct {
    WORD wButtons;
    BYTE bLeftTrigger, bRightTrigger;
    SHORT sThumbLX, sThumbLY, sThumbRX, sThumbRY;
} XInputGamepad;
typedef struct {
    DWORD dwPacketNumber;
    XInputGamepad Gamepad;
} XInputState;
typedef DWORD(WINAPI *XInputGetStateFn)(DWORD, XInputState *);

static HMODULE g_self;
static HMODULE g_real_dinput8;
static DirectInput8CreateFn g_real_create;
static InputUpdateFn g_original_update;
static XInputGetStateFn g_xinput_get_state;
static FILE *g_log;
static volatile LONG g_hook_attempted;
static unsigned long g_update_calls;

static void log_line(const char *fmt, ...)
{
    if (!g_log)
        return;
    SYSTEMTIME t;
    GetLocalTime(&t);
    fprintf(g_log, "%02u:%02u:%02u.%03u ", t.wHour, t.wMinute, t.wSecond, t.wMilliseconds);
    va_list ap;
    va_start(ap, fmt);
    vfprintf(g_log, fmt, ap);
    va_end(ap);
    fputc('\n', g_log);
    fflush(g_log);
}

static void open_log(void)
{
    char path[MAX_PATH];
    DWORD n = GetModuleFileNameA(g_self, path, MAX_PATH);
    char *slash = n ? strrchr(path, '\\') : NULL;
    if (!slash)
        return;
    strcpy(slash + 1, "dao_gamepad.log");
    g_log = fopen(path, "w");
    log_line("dao-gamepad stage0 (log only) loaded; module %p", (void *)g_self);
}

static int load_real_dinput8(void)
{
    if (g_real_create)
        return 1;
    char path[MAX_PATH];
    UINT n = GetSystemDirectoryA(path, MAX_PATH);
    if (!n || n + sizeof("\\dinput8.dll") > MAX_PATH)
        return 0;
    strcat(path, "\\dinput8.dll");
    g_real_dinput8 = LoadLibraryA(path);
    if (g_real_dinput8)
        g_real_create = (DirectInput8CreateFn)(void *)GetProcAddress(g_real_dinput8, "DirectInput8Create");
    log_line("system dinput8: %s -> module %p, DirectInput8Create %p", path, (void *)g_real_dinput8,
             (void *)g_real_create);
    return g_real_create != NULL;
}

static void probe_xinput(void)
{
    static const char *names[] = {"xinput1_4.dll", "xinput1_3.dll", "xinput9_1_0.dll"};
    for (size_t i = 0; i < sizeof(names) / sizeof(names[0]) && !g_xinput_get_state; i++) {
        HMODULE m = LoadLibraryA(names[i]);
        if (m)
            g_xinput_get_state = (XInputGetStateFn)(void *)GetProcAddress(m, "XInputGetState");
        log_line("xinput: %s -> module %p, XInputGetState %p", names[i], (void *)m,
                 (void *)g_xinput_get_state);
    }
}

static void log_pads(void)
{
    if (!g_xinput_get_state)
        return;
    for (DWORD pad = 0; pad < 4; pad++) {
        XInputState s;
        memset(&s, 0, sizeof s);
        DWORD rc = g_xinput_get_state(pad, &s);
        if (rc == ERROR_SUCCESS)
            log_line("pad %lu: connected packet=%lu buttons=%04x LT=%u RT=%u LX=%d LY=%d RX=%d RY=%d",
                     pad, s.dwPacketNumber, s.Gamepad.wButtons, s.Gamepad.bLeftTrigger,
                     s.Gamepad.bRightTrigger, s.Gamepad.sThumbLX, s.Gamepad.sThumbLY, s.Gamepad.sThumbRX,
                     s.Gamepad.sThumbRY);
    }
}

static void __attribute__((thiscall)) hooked_update(void *self, void *arg)
{
    g_original_update(self, arg);
    g_update_calls++;
    if (g_update_calls == 1)
        log_line("InputManager::Update first call: this=%p arg=%p", self, arg);
    if (g_update_calls % 600 == 0) {
        log_line("InputManager::Update calls=%lu", g_update_calls);
        log_pads();
    }
}

static void try_install_hook(void)
{
    if (InterlockedExchange(&g_hook_attempted, 1))
        return;
    char reason[160];
    if (!dao_build_matches(reason, sizeof reason)) {
        log_line("build check FAILED (%s); not hooking", reason);
        return;
    }
    void **slot = (void **)DAO_INPUTMGR_VTABLE_UPDATE_SLOT;
    DWORD old;
    if (!VirtualProtect(slot, sizeof(void *), PAGE_READWRITE, &old)) {
        log_line("VirtualProtect(%p) failed: %lu; not hooking", (void *)slot, GetLastError());
        return;
    }
    g_original_update = (InputUpdateFn)*slot;
    *slot = (void *)hooked_update;
    VirtualProtect(slot, sizeof(void *), old, &old);
    log_line("hooked InputManager vtable slot %p: %p -> %p", (void *)slot, (void *)g_original_update,
             (void *)hooked_update);
    probe_xinput();
    log_pads();
}

__declspec(dllexport) HRESULT WINAPI DirectInput8Create(HINSTANCE inst, DWORD version, REFIID riid, LPVOID *out,
                                                        LPUNKNOWN outer)
{
    log_line("DirectInput8Create(version=%#lx) called from %p", version, __builtin_return_address(0));
    try_install_hook();
    if (!load_real_dinput8())
        return E_FAIL;
    return g_real_create(inst, version, riid, out, outer);
}

BOOL WINAPI DllMain(HINSTANCE inst, DWORD reason, LPVOID reserved)
{
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH) {
        g_self = inst;
        DisableThreadLibraryCalls(inst);
        open_log();
    } else if (reason == DLL_PROCESS_DETACH) {
        log_line("unloading; InputManager::Update calls=%lu", g_update_calls);
        if (g_log)
            fclose(g_log);
    }
    return TRUE;
}
