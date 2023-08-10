// #if defined CK_WITH_INPUT_WRAPPERS
#include <stdio.h>

extern char *(*fgets_fp)(char *s, int size, FILE *stream);
extern char *(*scanf_fp)(const char *format, ...);

// define macros so user code refers to function pointers above
#define fgets fgets_fp
#define scanf scanf_fp

// #endif // CK_WITH_INPUT_WRAPPERS
