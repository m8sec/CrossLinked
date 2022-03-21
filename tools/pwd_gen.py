#!/usr/bin/env python3
# Author: m8r0wn
# License: GPLv3

# Output file location/name.txt
outfile = 'passwords.txt'

# Base words: company, first names, last names, etc (lowercase)
base = ['guest', 'password', 'welcome', 'admin', 'administrator', 'fall', 'winter', 'spring', 'summer']

# Prepend lowercase words, numbers, symbols, etc
prepend_chars = ['!', '#', '$', '@', '1']

# Append lowercase words, numbers, symbols, etc
append_chars = ['!', '#', '$', '@', '1', '01', '00', '#1', '21', '!21', '21!', '2021', '2021!', '#2021',
                '123', '123!', '!!', '69', '666', '1!']

# Combine select words with base words (welcome2company)
combine = ['welcome', 'guest', 'admin', 'password']

# Chars to connect two words (ex: welcome2company)
connecting_chars = ['@', '2']

# L3tt3r/Ch4r Subst1tut10n
substitution = True
########################################################################
from os import path, remove
from sys import exit

def outfile_prep():
    # check if file exists and prompt user to delete
    if path.exists(outfile):
        print("[!] Output file '{}' already exists".format(outfile))
        delete_old = input("[*] Do you want to delete and continue? [y/N]: ")
        if delete_old.strip() not in ['y', 'Y']:
            exit(0)
        remove(outfile)

def main():
    basemod = []  
    outfile_prep()
    print('\n[*] Generating password combinations')

    basemod2 = []
    if substitution:
        word_lists = [combine, base]
        for word_list in word_lists:
            for x in word_list:
                basemod2.append(x.replace('o', '0'))
                basemod2.append(x.replace('a', '4'))
                basemod2.append(x.replace('a', '@'))
                basemod2.append(x.replace('l', '1'))
                basemod2.append(x.replace('l', '!'))
                basemod2.append(x.replace('i', '1'))
                basemod2.append(x.replace('i', '!'))
                basemod2.append(x.replace('e', '3'))
                basemod2.append(x.replace('s', '$'))
                basemod2.append(x.replace('a', '@').replace('i', '!'))
                basemod2.append(x.replace('a', '@').replace('i', '1'))
                basemod2.append(x.replace('s', '$').replace('e', '3'))
                basemod2.append(x.replace('o', '0').replace('e', '3'))
                basemod2.append(x.replace('o', '0').replace('l', '1').replace('e', '3'))
                basemod2.append(x.replace('o', '0').replace('l', '!').replace('e', '3'))
                basemod2.append(x.replace('o', '0').replace('i', '1').replace('e', '3'))
                basemod2.append(x.replace('o', '0').replace('i', '!').replace('e', '3'))
                basemod2.append(x.replace('o', '0').replace('l', '1').replace('a', '4').replace('e', '3'))
                basemod2.append(x.replace('o', '0').replace('l', '1').replace('a', '@').replace('e', '3'))
                basemod2.append(x.replace('o', '0').replace('l', '!').replace('a', '4').replace('e', '3'))
                basemod2.append(x.replace('o', '0').replace('l', '!').replace('a', '@').replace('e', '3'))
                basemod2.append(
                    x.replace('o', '0').replace('l', '1').replace('a', '4').replace('e', '3').replace('s', '$'))
                basemod2.append(
                    x.replace('o', '0').replace('l', '1').replace('a', '@').replace('e', '3').replace('s', '$'))
                basemod2.append(
                    x.replace('o', '0').replace('l', '!').replace('a', '4').replace('e', '3').replace('s', '$'))
                basemod2.append(
                    x.replace('o', '0').replace('l', '!').replace('a', '@').replace('e', '3').replace('s', '$'))
        basemod2 = list(set(basemod2))

    word_lists = [basemod2, base]
    for word_list in word_lists:
        for x in word_list:
            basemod.append(x)
            basemod.append(x.upper())
            basemod.append(x.title())

            for y in prepend_chars:
                basemod.append(y + x)
                basemod.append(y + x.title())
                basemod.append(y + x.upper())

            for y in append_chars:
                basemod.append(x + y)
                basemod.append(x.title() + y)
                basemod.append(x.upper() + y)

            for y in combine:
                if x != y:
                    # switch x & y without repeating entire block of code
                    for switch in [0, 1]:
                        if switch == 1:
                            a = x
                            b = y
                        else:
                            a = y
                            b = x
                        basemod.append(a + b)
                        basemod.append(a + b.upper())
                        basemod.append(a + b.title())

                        basemod.append(a.upper() + b)
                        basemod.append(a.title() + b)

                        basemod.append(a.upper() + b.upper())
                        basemod.append(a.title() + b.upper())
                        basemod.append(a.upper() + b.title())
                        basemod.append(a.title() + b.title())

                        for z in append_chars:
                            basemod.append(a + b + z)
                            basemod.append(a + b.upper() + z)
                            basemod.append(a + b.title() + z)

                            basemod.append(a.upper() + b + z)
                            basemod.append(a.title() + b + z)

                            basemod.append(a.upper() + b.upper() + z)
                            basemod.append(a.title() + b.upper() + z)
                            basemod.append(a.upper() + b.title() + z)
                            basemod.append(a.title() + b.title() + z)

                        for z in prepend_chars:
                            basemod.append(z + a + b)
                            basemod.append(z + a + b.upper())
                            basemod.append(z + a + b.title())

                            basemod.append(z + a.upper() + b)
                            basemod.append(z + a.title() + b)

                            basemod.append(z + a.upper() + b.upper())
                            basemod.append(z + a.title() + b.upper())
                            basemod.append(z + a.upper() + b.title())
                            basemod.append(z + a.title() + b.title())

                        for z in connecting_chars:
                            basemod.append(a + z + b)
                            basemod.append(a + z + b.upper())
                            basemod.append(a + z + b.title())

                            basemod.append(a.upper() + z + b)
                            basemod.append(a.title() + z + b)

                            basemod.append(a.upper() + z + b.upper())
                            basemod.append(a.title() + z + b.upper())
                            basemod.append(a.upper() + z + b.title())
                            basemod.append(a.title() + z + b.title())

    print('[*] Removing potential duplicates...')
    basemod = list(set(basemod))
    print('[*] {} Unique words created'.format(str(len(basemod))))
    print('[*] Writing to {}'.format(outfile))

    # Deduplicate and write to file
    openFile = open(outfile, 'w')
    for x in basemod:
        openFile.write('{}\n'.format(x))
    openFile.close()

    print("\n[+] Password list complete!\n")

if __name__ == '__main__':
    VERSION = "0.0.2"
    main()