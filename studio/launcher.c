#define _GNU_SOURCE
#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>
int main(int argc, char **argv) {
 char path[PATH_MAX], script[PATH_MAX];
 ssize_t n=readlink("/proc/self/exe",path,sizeof(path)-1);
 if(n<0)return 1;
 path[n]=0; char *end=strrchr(path,'/'); if(!end)return 1; *end=0;
 if(snprintf(script,sizeof script,"%s/../studio/app.py",path)>=(int)sizeof script)return 1;
 if(access(script,R_OK))snprintf(script,sizeof script,"/usr/lib/optiplex-studio/app.py");
 execl("/usr/bin/python3","python3",script,(char*)NULL);
 perror("OptiPlex Studio");return 1;
}
