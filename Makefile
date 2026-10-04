CC      := i686-w64-mingw32-gcc
CFLAGS  := -std=c11 -O2 -Wall -Wextra -Werror -Isrc
LDFLAGS := -shared -static-libgcc -Wl,--kill-at -Wl,--enable-stdcall-fixup

BUILD := build
SRCS  := src/dinput8_proxy.c src/dao_build.c

.PHONY: all test clean

all: $(BUILD)/dinput8.dll

$(BUILD)/dinput8.dll: $(SRCS) src/dao_build.h | $(BUILD)
	$(CC) $(CFLAGS) -o $@ $(SRCS) $(LDFLAGS)

$(BUILD):
	mkdir -p $@

test: all
	python3 -m unittest discover -s tests -p 'test_*.py'

clean:
	rm -rf $(BUILD)
