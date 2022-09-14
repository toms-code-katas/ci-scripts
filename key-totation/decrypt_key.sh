#!/usr/bin/expect -f

set timeout -1
set key_password [lindex $argv 0];
set key_file [lindex $argv 1];

spawn bash -c "age -d $key_file > $key_file.txt"

expect -re "Enter passphrase" {
    send "$key_password\r"
}

expect eof