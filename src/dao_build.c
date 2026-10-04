#include <windows.h>
#include <stdio.h>
#include <string.h>

#include "dao_build.h"

/* InputManager vtable contents in the pinned build. */
static const DWORD k_vtable[4] = {0x008804d0u, 0x008804f0u, 0x0087e350u, 0x0087df20u};

/* First bytes of InputManager::Update: push esi; push edi; mov edi,[esp+0xc]; mov esi,ecx. */
static const BYTE k_update_prologue[8] = {0x56, 0x57, 0x8b, 0x7c, 0x24, 0x0c, 0x8b, 0xf1};

static int readable(const void *p, size_t n)
{
    MEMORY_BASIC_INFORMATION mbi;
    if (!VirtualQuery(p, &mbi, sizeof mbi) || mbi.State != MEM_COMMIT)
        return 0;
    if (mbi.Protect & (PAGE_NOACCESS | PAGE_GUARD))
        return 0;
    return (const BYTE *)p + n <= (const BYTE *)mbi.BaseAddress + mbi.RegionSize;
}

int dao_build_matches(char *reason, size_t reason_len)
{
    HMODULE exe = GetModuleHandleA(NULL);
    if ((DWORD)(UINT_PTR)exe != DAO_IMAGE_BASE) {
        snprintf(reason, reason_len, "image base %p != %#x", (void *)exe, DAO_IMAGE_BASE);
        return 0;
    }
    const DWORD *vt = (const DWORD *)DAO_INPUTMGR_VTABLE;
    if (!readable(vt, sizeof k_vtable) || memcmp(vt, k_vtable, sizeof k_vtable) != 0) {
        snprintf(reason, reason_len, "InputManager vtable at %#x does not match", DAO_INPUTMGR_VTABLE);
        return 0;
    }
    const BYTE *fn = (const BYTE *)DAO_INPUTMGR_UPDATE;
    if (!readable(fn, sizeof k_update_prologue) || memcmp(fn, k_update_prologue, sizeof k_update_prologue) != 0) {
        snprintf(reason, reason_len, "Update prologue at %#x does not match (still encrypted?)", DAO_INPUTMGR_UPDATE);
        return 0;
    }
    snprintf(reason, reason_len, "ok");
    return 1;
}
