/*
 * Pinned facts about the supported DAOrigins.exe build (Steam buildid 21245176,
 * sha256 400c2c9e97bb1a534121553be66f202429ef6f7320c93c86f9b7a491864647bd).
 * Source: notes/phase1-recon.md. The image has no ASLR, so these VAs are fixed.
 */
#ifndef DAO_BUILD_H
#define DAO_BUILD_H

#include <stddef.h>

#define DAO_IMAGE_BASE 0x00400000u
#define DAO_INPUTMGR_VTABLE 0x00b2ed28u
#define DAO_INPUTMGR_VTABLE_UPDATE_SLOT (DAO_INPUTMGR_VTABLE + 4u)
#define DAO_INPUTMGR_UPDATE 0x008804f0u

/* Returns 1 when the running image matches the pinned build; otherwise 0 and a reason. */
int dao_build_matches(char *reason, size_t reason_len);

#endif
