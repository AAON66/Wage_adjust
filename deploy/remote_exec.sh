#!/usr/bin/expect -f
# 用法: ./remote_exec.sh "远程命令"
set timeout 300
set cmd [lindex $argv 0]
spawn ssh -o StrictHostKeyChecking=no root@10.0.0.60 "bash -c {$cmd}"
expect {
    "password:" { send "gQJwgfG9obG57p\r"; exp_continue }
    eof
}
foreach {pid spawnid os_error value} [wait] break
exit $value
