/**
 * `#define _GNU_SOURCE` required for RTLD_NEXT. Note that this affects how the
 * scanf-family's names are #defined, so any user code requiring input should
 * also define _GNU_SOURCE
 *
 */
#define _GNU_SOURCE

#include <dlfcn.h> // for dlsym
#include <errno.h>
#include <fcntl.h> // for O_ constants
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/sem.h>
#include <sys/stat.h> // struct stat

#define USE_C11 (__STDC_VERSION__ >= 201112L)
#define USE_BOUNDS_CHECKING                                                    \
  ((defined(__STDC_LIB_EXT1__)) && (__STDC_WANT_LIB_EXT1__ >= 1))
#define NEED_gets (!(USE_C11))
#define NEED_gets_s ((USE_C11) && USE_BOUNDS_CHECKING)
#define NEED_getdelim                                                          \
  (defined(_GNU_SOURCE) ||                                                     \
   (defined(_POSIX_C_SOURCE) && (_POSIX_C_SOURCE >= 200809L)))
#define NEED_FN(fn) NEED_##fn

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

#define CKERROR(fmt, n, s, ...)                                                \
  fprintf(stderr, "%s:%d in %s: [Error %d: %s] " fmt "\n", __FILE__, __LINE__, \
          __func__, (n), ((s) ? (s) : "(none)")PASS_ARGS(__VA_ARGS__))

#if defined CKERNEL_WITH_DEBUG
  #define CKDEBUG(fmt, ...)                                                    \
    fprintf(stdout, "[D] %s:%d in %s: " fmt "\n", __FILE__, __LINE__,          \
            __func__ PASS_ARGS(__VA_ARGS__))
#else
  #define CKDEBUG(fmt, ...)
#endif

#define FP(name) name##_fp
#define ATTACH_FP(s, name)                                                     \
  do {                                                                         \
    if ((s.name = dlsym(RTLD_NEXT, #name)) == NULL)                            \
      CKERROR("failed to find symbol %s", 0, NULL, #name);                     \
    else {                                                                     \
      CKDEBUG("attached symbol %s", #name);                                    \
    }                                                                          \
  } while (0)

static bool request_input = false;
key_t stdin_semkey = -1;
int stdin_semid = -1;

// pointers to real input functions
struct input_fp {
  int (*fgetc)(FILE *);
  char *(*fgets)(char *, int, FILE *);
#if NEED_FN(gets_s)
  char *(*gets_s)(char *, rsize_t);
#endif
#if NEED_FN(gets)
  char *(*gets)(char *);
#endif
  int (*getchar)(void);
  int (*vfscanf)(FILE *, const char *, va_list);
#if USE_C11 && USE_BOUNDS_CHECKING
  int (*vfscanf_s)(FILE *, const char *, va_list);
#endif
#if NEED_getdelim
  ssize_t (*getdelim)(char **, size_t *, int, FILE *);
#endif
};

static struct input_fp ifp = {0};

static void ck_request_input(FILE *stream);

static void __attribute__((constructor)) ck_setup(void) {
  struct stat stdin_stat;
  fstat(fileno(stdin), &stdin_stat);

#if defined(CKERNEL_WITH_DEBUG)
  const char *file_type = NULL;
  switch (stdin_stat.st_mode & S_IFMT) {
  case S_IFBLK:
    file_type = "block device";
    break;
  case S_IFCHR:
    file_type = "character device";
    break;
  case S_IFDIR:
    file_type = "directory";
    break;
  case S_IFIFO:
    file_type = "FIFO/pipe";
    break;
  case S_IFLNK:
    file_type = "symlink";
    break;
  case S_IFREG:
    file_type = "regular file"; // i.e. redirected from file
    break;
  case S_IFSOCK:
    file_type = "socket";
    break;
  default:
    file_type = "unknown?";
    break;
  }
  CKDEBUG("%-16s %s", "file type", file_type);
  CKDEBUG("%-16s %d", "st_dev",
          stdin_stat.st_dev); /* ID of device containing file */
  CKDEBUG("%-16s %d", "st_ino", stdin_stat.st_ino);    /* Inode number */
  CKDEBUG("%-16s 0%o", "st_mode", stdin_stat.st_mode); /* File type and mode */
  CKDEBUG("%-16s %d", "st_nlink",
          stdin_stat.st_nlink);                     /* Number of hard links */
  CKDEBUG("%-16s %d", "st_uid", stdin_stat.st_uid); /* User ID of owner */
  CKDEBUG("%-16s %d", "st_gid", stdin_stat.st_gid); /* Group ID of owner */
  CKDEBUG("%-16s %d", "st_rdev",
          stdin_stat.st_rdev); /* Device ID (if special file) */
  CKDEBUG("%-16s %d", "st_size", stdin_stat.st_size); /* Total size, in bytes */
  CKDEBUG("%-16s %d", "st_blksize",
          stdin_stat.st_blksize); /* Block size for filesystem I/O */
  CKDEBUG("%-16s %d", "st_blocks",
          stdin_stat.st_blocks); /* Number of 512 B blocks allocated */
#endif

  // if stdin is NOT a regular file, use semaphore for input request
  CKDEBUG("%s", S_ISREG(stdin_stat.st_mode) ? "stdin is regular file"
                                            : "stdin is not regular file");
  request_input = (!(S_ISREG(stdin_stat.st_mode))) ? true : false;

  if (setvbuf(stdout, NULL, _IONBF, 0) != 0) {
    CKERROR("failed to set stdout to unbuffered", errno, strerror(errno));
  }

  // point to actual input functions
  ATTACH_FP(ifp, fgetc);
  ATTACH_FP(ifp, fgets);
#if NEED_FN(gets_s)
  ATTACH_FP(ifp, gets_s);
#endif
#if NEED_FN(gets)
  ATTACH_FP(ifp, gets);
#endif
  ATTACH_FP(ifp, getchar);
  ATTACH_FP(ifp, vfscanf);
#if USE_C11 && USE_BOUNDS_CHECKING
  ATTACH_FP(ifp, vfscanf_s);
#endif
#if NEED_getdelim
  ATTACH_FP(ifp, getdelim);
#endif

  // get the specified semaphore from the environment
  const char *sem_key = NULL;
  if ((sem_key = getenv("CK_SEMKEY")) == NULL) {
    CKDEBUG("environment variable %s not set, no semaphore specified",
            "CK_SEMKEY");
    request_input = false;
    return;
  }

  // attempt to get semaphore
  CKDEBUG("get semaphore key %s", sem_key);
  key_t _key = -1;
  sscanf(sem_key, "%d", &_key);
  if ((stdin_semid = semget(_key, 1, 0)) == -1) {
    CKDEBUG("failed to get semaphore with key=%s, not using input wrappers "
            "[Error %d: %s]",
            sem_key, errno, strerror(errno));
    request_input = false;
  } else {
    CKDEBUG("got semaphore with key=%s, id=%d\n", sem_key, stdin_semid);
  }
  return;
}

static void ck_request_input(FILE *stream) {
  if (!(request_input && (stream == stdin)))
    return;
  CKDEBUG("signal waiting for input");
  struct sembuf op = {.sem_num = 0, .sem_op = +1, .sem_flg = 0};
  if (semop(stdin_semid, &op, 1) == -1) {
    CKDEBUG("failed to increment semaphore id=%d "
            "[Error %d: %s]",
            stdin_semid, errno, strerror(errno));
  }
  CKDEBUG("ready for input");
}

int getc(FILE *stream) {
  CKDEBUG("requesting input");
  ck_request_input(stream);
  return ifp.fgetc(stream);
}

int fgetc(FILE *stream) {
  CKDEBUG("requesting input");
  ck_request_input(stream);
  return ifp.fgetc(stream);
}

#if NEED_FN(gets_s)
char *gets_s(char *str, rsize_t n) {
  CKDEBUG("requesting input");
  ck_request_input(stdin);
  return ifp.gets_s(str, n);
}
#endif

#if NEED_FN(gets)
char *gets(char *str) {
  CKDEBUG("requesting input");
  ck_request_input(stdin);
  return ifp.gets(str);
}
#endif

char *fgets(char *s, int size, FILE *stream) {
  CKDEBUG("requesting input");
  ck_request_input(stream);
  return ifp.fgets(s, size, stream);
}

int getchar(void) {
  CKDEBUG("requesting input");
  ck_request_input(stdin);
  return ifp.getchar();
}

/**
 * @brief A wrapper around ifp.vfscanf which gets input and then, if stream is
 * stdin, eats input until the next '\n' or EOF.
 */
int vfscanf_and_eat_newline(FILE *stream, const char *format, va_list args) {
  int result = ifp.vfscanf(stdin, format, args);
  if (stream == stdin) {
    CKDEBUG("consuming stdin until newline removed or EOF");
    int c = EOF;
    do {
      c = ifp.fgetc(stream);
    } while ((c != '\n') && (c != EOF));
    CKDEBUG("finished consuming stdin");
  }
  return result;
}

int scanf(const char *format, ...) {
  CKDEBUG("requesting input");
  ck_request_input(stdin);
  va_list args;
  va_start(args, format);
  int result = vfscanf_and_eat_newline(stdin, format, args);
  va_end(args);
  return result;
}

int fscanf(FILE *stream, const char *format, ...) {
  CKDEBUG("requesting input");
  ck_request_input(stream);
  va_list args;
  va_start(args, format);
  int result = vfscanf_and_eat_newline(stream, format, args);
  va_end(args);
  return result;
}

int vscanf(const char *format, va_list args) {
  CKDEBUG("requesting input");
  ck_request_input(stdin);
  return vfscanf_and_eat_newline(stdin, format, args);
}

int vfscanf(FILE *stream, const char *format, va_list args) {
  CKDEBUG("requesting input");
  ck_request_input(stream);
  return vfscanf_and_eat_newline(stream, format, args);
}

#if USE_C11 && USE_BOUNDS_CHECKING
int scanf_s(const char *format, ...) {
  CKDEBUG("requesting input");
  ck_request_input(stdin);
  va_list args;
  va_start(args, format);
  int result = ifp.vfscanf_s(stdin, format, args);
  va_end(args);
  return result;
}

int fscanf_s(FILE *restrict stream, const char *restrict format, ...) {
  CKDEBUG("requesting input");
  ck_request_input(stream);
  va_list args;
  va_start(args, format);
  int result = ifp.vfscanf_s(stream, format, args);
  va_end(args);
  return result;
}

int vscanf_s(const char *format, va_list args) {
  CKDEBUG("requesting input");
  ck_request_input(stdin);
  return ifp.vfscanf_s(stdin, format, args);
}

int vfscanf_s(FILE *stream, const char *format, va_list args) {
  CKDEBUG("requesting input");
  ck_request_input(stream);
  return ifp.vfscanf_s(stream, format, args);
}
#endif

#if NEED_FN(getdelim)
ssize_t getline(char **lineptr, size_t *n, FILE *stream) {
  CKDEBUG("requesting input");
  ck_request_input(stream);
  return ifp.getdelim(lineptr, n, '\n', stream);
}

ssize_t getdelim(char **lineptr, size_t *n, int delimiter, FILE *stream) {
  CKDEBUG("requesting input");
  ck_request_input(stream);
  return ifp.getdelim(lineptr, n, delimiter, stream);
}
#endif
