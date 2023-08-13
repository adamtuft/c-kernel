#define _GNU_SOURCE
#include <stdlib.h>
#include <stdio.h>
#include <errno.h>
#include <string.h>
#include <stdarg.h>
#include <stdbool.h>
#include <mqueue.h>
#include <sys/stat.h> // struct stat
#include <fcntl.h>    // for O_ constants
#include <dlfcn.h>    // for dlsym

/**
 * TODO:
 * add wrappers for other standard input functions:
 *
 * read directly from stdin:
 *  - getchar
 *  - gets (before C11) /gets_s (since C11)
 *  - vscanf
 *
 * read from a file stream:
 *  - (f)getc
 *  - fgets
 *  - ungetc
 *  - scanf_s (c11)
 *  - fscanf(_s (c11))
 *  - sscanf(_s (c11))
 *  - vscanf_s (c11)
 *  - vfscanf(_s (c11))
 *  - vsscanf(_s (c11))
 *
 */

#define THIRD_ARG(a, b, c, ...) c
#define VA_OPT_AVAIL_I(...) THIRD_ARG(__VA_OPT__(, ), 1, 0, )
#define VA_OPT_AVAIL VA_OPT_AVAIL_I(?)
#if VA_OPT_AVAIL
#define PASS_ARGS_I(...) __VA_OPT__(, ) __VA_ARGS__
#else
#define PASS_ARGS_I(...) , ##__VA_ARGS__
#endif
#undef THIRD_ARG
#undef VA_OPT_AVAIL_I
#undef VA_OPT_AVAIL
#define PASS_ARGS(...) PASS_ARGS_I(__VA_ARGS__)

#define CKERROR(fmt, n, s, ...) \
    fprintf(stderr, "%s:%d in %s: [Error %d: %s] " fmt "\n", __FILE__, __LINE__, __func__, (n), ((s) ? (s) : "(none)")PASS_ARGS(__VA_ARGS__))

#if defined CKERNEL_WITH_DEBUG
#define CKDEBUG(fmt, ...) \
    fprintf(stdout, "[D] %s:%d in %s: " fmt "\n", __FILE__, __LINE__, __func__ PASS_ARGS(__VA_ARGS__))
#else
#define CKDEBUG(fmt, ...)
#endif

#define FP(name) name##_fp
#define ATTACH_FP(name)                                          \
    do                                                           \
    {                                                            \
        if ((FP(name) = dlsym(RTLD_NEXT, #name)) == NULL)        \
            CKERROR("failed to find symbol %s", 0, NULL, #name); \
        else                                                     \
        {                                                        \
            CKDEBUG("attached symbol %s", #name);                \
        }                                                        \
    } while (0)

static bool request_input = false;
static mqd_t stdin_mq = -1;

// pointers to real input functions
char *(*FP(fgets))(char *s, int size, FILE *stream) = NULL;
int (*FP(scanf))(const char *format, ...) = NULL;

// input wrapper functions
char *fgets(char *s, int size, FILE *stream);
int scanf(const char *format, ...);

static void __attribute__((constructor)) ck_setup(void)
{
    struct stat stdin_stat;
    fstat(fileno(stdin), &stdin_stat);

    // if stdin is FIFO (i.e. from subprocess.PIPE), use message queue for input request
    CKDEBUG("%s", (stdin_stat.st_mode & S_IFIFO) ? "stdin is FIFO" : "stdin is not FIFO");
    request_input = (stdin_stat.st_mode & S_IFIFO) ? true : false;

    if (setvbuf(stdout, NULL, _IONBF, 0) != 0)
    {
        CKERROR("failed to set stdout to unbuffered", errno, strerror(errno));
    }

    // point to actual input functions
    ATTACH_FP(fgets);
    ATTACH_FP(scanf);

    // attempt to connect to message queue
    const char *mq_name = NULL;
    if ((mq_name = getenv("CK_MQNAME")) == NULL)
        mq_name = "NONE";
    CKDEBUG("connect to queue %s", mq_name);
    if ((stdin_mq = mq_open(mq_name, O_WRONLY)) == -1)
    {
        CKDEBUG("failed to open message queue, not using input wrappers [Error %d: %s]", errno, strerror(errno));
        request_input = false;
    }
    return;
}

static void mq_request_input(void)
{
    if (!request_input)
        return;
    static const char *msg = "READY";
    CKDEBUG("signal waiting for input");
    mq_send(stdin_mq, msg, strlen(msg), 0);
    CKDEBUG("ready for input");
}

char *fgets(char *s, int size, FILE *stream)
{
    mq_request_input();
    char *result = fgets_fp(s, size, stream);
    return result;
}

int scanf(const char *format, ...)
{
    mq_request_input();
    va_list args;
    va_start(args, format);
    int result = vscanf(format, args);
    va_end(args);
    return result;
}
