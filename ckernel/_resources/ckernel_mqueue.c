#include <stdlib.h>
#include <stdio.h>
#include <errno.h>
#include <string.h>
#include <stdarg.h>
#include <mqueue.h>
#include <sys/stat.h> // struct stat
#include <fcntl.h>    // for O_ constants
#include <dlfcn.h>    // for dlsym

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

static mqd_t stdin_mq = -1;

static char *(*fgets_fp)(char *s, int size, FILE *stream) = NULL;

static char *ck_fgets(char *s, int size, FILE *stream);

static void __attribute__((constructor)) ck_setup(void)
{

    struct stat stdin_stat;
    fstat(fileno(stdin), &stdin_stat);

    if (!(stdin_stat.st_mode & S_IFIFO))
    {
        // stdin is not a FIFO (i.e. not from subprocess.PIPE), so don't use message queue for input request
        CKDEBUG("stdin is not FIFO");
        fgets_fp = fgets;
        return;
    }

    if (setvbuf(stdout, NULL, _IONBF, 0) != 0)
    {
        CKERROR("failed to set stdout to unbuffered", errno, strerror(errno));
    }

    // point to IO wrapper functions
    fgets_fp = ck_fgets;

    const char *mq_name = NULL;
    if ((mq_name = getenv("CK_MQNAME")) == NULL)
        mq_name = "NONE";
    CKDEBUG("connect to queue %s", mq_name);
    if ((stdin_mq = mq_open(mq_name, O_WRONLY)) == -1)
    {
        CKERROR("failed to open message queue", errno, strerror(errno));
        abort();
    }
    return;
}

static char *ck_fgets(char *s, int size, FILE *stream)
{
    static const char *msg = "READY";
    CKDEBUG("signal waiting for input");
    mq_send(stdin_mq, msg, strlen(msg), 0);
    CKDEBUG("ready for input");
    char *result = fgets(s, size, stream);
    return result;
}
