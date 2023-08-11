#if !defined(CKERNEL_MQUEUE_H)
#define CKERNEL_MQUEUE_H

#include <stdio.h>

extern char *(*fgets_fp)(char *s, int size, FILE *stream);
extern char *(*scanf_fp)(const char *format, ...);

// define macros so user code refers to function pointers above
#define fgets fgets_fp
#define scanf scanf_fp

#endif // CKERNEL_MQUEUE_H
