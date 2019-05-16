#!/usr/bin/env python3
# Author: @m8r0wn

# outfile
outfile = 'passwords.txt'

# Base words: company, first names, last names, etc (lowercase)
base = ['password','welcome','spring','summer','winter','fall','administrator','admin', ]

# Combine words in base list and proceed to append/prepend
blend = False

# Prepend values (lowercase) (ex. google, google_, google-)
prepend_words = []
prepend_chars = []

# Append values (lowercase) (ex. google, _google, -google)
append_words = []
append_chars = ['$', '!','1!', '123', '#1', '123!', '!1', '1', '2019', '2019!']

# L3tt3r/Ch4r Subst1tut10n on base words
substitution = True

# Perform substitution on word combinations from append_words & base
combine = False

########################################################################
def main():
    basemod = []                #Main base modification list
    basemod_append_words = []   #Temp list for base mod + append_chars for substitution

    #Start word modification
    for x in base:
        basemod.append(x)
        basemod.append(x.upper())
        basemod.append(x.title())
        if blend:
            for y in reversed(base):
                if y != x:
                    basemod.append(x+y)
                    basemod.append(x.title()+y)
                    basemod.append(x + y.title())
                    basemod.append(x.upper() + y.upper())
                    basemod.append(x.title() + y.title())

                    if substitution and combine:
                        basemod_append_words.append(x + y)
                        basemod_append_words.append(x.title() + y)
                        basemod_append_words.append(x + y.title())
                        basemod_append_words.append(x.upper() + y.upper())
                        basemod_append_words.append(x.title() + y.title())

                    if append_chars:
                        for z in append_chars:
                            basemod.append(x + y+z)
                            basemod.append(x.title() + y+z)
                            basemod.append(x + y.title()+z)
                            basemod.append(x.upper() + y.upper()+z)
                            basemod.append(x.title() + y.title()+z)

    for x in base:
        if append_chars:
            for y in append_chars:
                basemod.append(x + y)
                basemod.append(x.title() + y)
                basemod.append(x.upper() + y)

        if append_words:
            for y in append_words:
                basemod.append(x + y)
                basemod.append(x.title() + y)
                basemod.append(x + y.title())
                basemod.append(x.upper() + y.upper())
                basemod.append(x.title() + y.title())

                if substitution and combine:
                    basemod_append_words.append(x + y)
                    basemod_append_words.append(x.title() + y)
                    basemod_append_words.append(x + y.title())
                    basemod_append_words.append(x.upper() + y.upper())
                    basemod_append_words.append(x.title() + y.title())

                if append_chars:
                    for z in append_chars:
                        basemod.append(x + y+z)
                        basemod.append(x.title() + y+z)
                        basemod.append(x + y.title()+z)
                        basemod.append(x.upper() + y.upper()+z)
                        basemod.append(x.title() + y.title()+z)

                        if substitution and combine:
                            basemod_append_words.append(x + y + z)
                            basemod_append_words.append(x.title() + y + z)
                            basemod_append_words.append(x + y.title() + z)
                            basemod_append_words.append(x.upper() + y.upper() + z)
                            basemod_append_words.append(x.title() + y.title() + z)

        if prepend_chars:
            for y in prepend_chars:
                basemod.append(y+x)

        if prepend_words:
            for y in prepend_words:
                basemod.append(y+x)
                basemod.append(y+ x.title())
                basemod.append(y.title()+x)
                basemod.append(y.upper() + x.upper())
                basemod.append(y.title() + x.title())

    if substitution:
        for x in base:
            basemod.append(x.replace('o', '0'))
            basemod.append(x.replace('a', '4'))
            basemod.append(x.replace('a', '@'))
            basemod.append(x.replace('l', '1'))
            basemod.append(x.replace('l', '!'))
            basemod.append(x.replace('i', '1'))
            basemod.append(x.replace('i', '!'))
            basemod.append(x.replace('e', '3'))
            basemod.append(x.replace('s', '$'))
            basemod.append(x.replace('a', '@').replace('i', '!'))
            basemod.append(x.replace('a', '@').replace('i', '1'))
            basemod.append(x.replace('s', '$').replace('e', '3'))
            basemod.append(x.replace('o', '0').replace('e', '3'))
            basemod.append(x.replace('o', '0').replace('l', '1').replace('e', '3'))
            basemod.append(x.replace('o', '0').replace('l', '!').replace('e', '3'))
            basemod.append(x.replace('o', '0').replace('i', '1').replace('e', '3'))
            basemod.append(x.replace('o', '0').replace('i', '!').replace('e', '3'))
            basemod.append(x.replace('o', '0').replace('l', '1').replace('a', '4').replace('e', '3'))
            basemod.append(x.replace('o', '0').replace('l', '1').replace('a', '@').replace('e', '3'))
            basemod.append(x.replace('o', '0').replace('l', '!').replace('a', '4').replace('e', '3'))
            basemod.append(x.replace('o', '0').replace('l', '!').replace('a', '@').replace('e', '3'))
            basemod.append(x.replace('o', '0').replace('l', '1').replace('a', '4').replace('e', '3').replace('s', '$'))
            basemod.append(x.replace('o', '0').replace('l', '1').replace('a', '@').replace('e', '3').replace('s', '$'))
            basemod.append(x.replace('o', '0').replace('l', '!').replace('a', '4').replace('e', '3').replace('s', '$'))
            basemod.append(x.replace('o', '0').replace('l', '!').replace('a', '@').replace('e', '3').replace('s', '$'))

            #Subtitution x.title()
            basemod.append(x.title().replace('o', '0'))
            basemod.append(x.title().replace('a', '4'))
            basemod.append(x.title().replace('a', '@'))
            basemod.append(x.title().replace('l', '1'))
            basemod.append(x.title().replace('l', '!'))
            basemod.append(x.title().replace('i', '1'))
            basemod.append(x.title().replace('i', '!'))
            basemod.append(x.title().replace('e', '3'))
            basemod.append(x.title().replace('s', '$'))
            basemod.append(x.title().replace('a', '@').replace('i', '!'))
            basemod.append(x.title().replace('a', '@').replace('i', '1'))
            basemod.append(x.title().replace('s', '$').replace('e', '3'))
            basemod.append(x.title().replace('o', '0').replace('e', '3'))
            basemod.append(x.title().replace('o', '0').replace('l', '1').replace('e', '3'))
            basemod.append(x.title().replace('o', '0').replace('l', '!').replace('e', '3'))
            basemod.append(x.title().replace('o', '0').replace('i', '1').replace('e', '3'))
            basemod.append(x.title().replace('o', '0').replace('i', '!').replace('e', '3'))
            basemod.append(x.title().replace('o', '0').replace('l', '1').replace('a', '4').replace('e', '3'))
            basemod.append(x.title().replace('o', '0').replace('l', '1').replace('a', '@').replace('e', '3'))
            basemod.append(x.title().replace('o', '0').replace('l', '!').replace('a', '4').replace('e', '3'))
            basemod.append(x.title().replace('o', '0').replace('l', '!').replace('a', '@').replace('e', '3'))
            basemod.append(x.title().replace('o', '0').replace('l', '1').replace('a', '4').replace('e', '3').replace('s', '$'))
            basemod.append(x.title().replace('o', '0').replace('l', '1').replace('a', '@').replace('e', '3').replace('s', '$'))
            basemod.append(x.title().replace('o', '0').replace('l', '!').replace('a', '4').replace('e', '3').replace('s', '$'))
            basemod.append(x.title().replace('o', '0').replace('l', '!').replace('a', '@').replace('e', '3').replace('s', '$'))

            #Subtitution x.upper()
            basemod.append(x.upper().replace('o', '0'))
            basemod.append(x.upper().replace('a', '4'))
            basemod.append(x.upper().replace('a', '@'))
            basemod.append(x.upper().replace('l', '1'))
            basemod.append(x.upper().replace('l', '!'))
            basemod.append(x.upper().replace('i', '1'))
            basemod.append(x.upper().replace('i', '!'))
            basemod.append(x.upper().replace('e', '3'))
            basemod.append(x.upper().replace('s', '$'))
            basemod.append(x.upper().replace('a', '@').replace('i', '!'))
            basemod.append(x.upper().replace('a', '@').replace('i', '1'))
            basemod.append(x.upper().replace('s', '$').replace('e', '3'))
            basemod.append(x.upper().replace('o', '0').replace('e', '3'))
            basemod.append(x.upper().replace('o', '0').replace('l', '1').replace('e', '3'))
            basemod.append(x.upper().replace('o', '0').replace('l', '!').replace('e', '3'))
            basemod.append(x.upper().replace('o', '0').replace('i', '1').replace('e', '3'))
            basemod.append(x.upper().replace('o', '0').replace('i', '!').replace('e', '3'))
            basemod.append(x.upper().replace('o', '0').replace('l', '1').replace('a', '4').replace('e', '3'))
            basemod.append(x.upper().replace('o', '0').replace('l', '1').replace('a', '@').replace('e', '3'))
            basemod.append(x.upper().replace('o', '0').replace('l', '!').replace('a', '4').replace('e', '3'))
            basemod.append(x.upper().replace('o', '0').replace('l', '!').replace('a', '@').replace('e', '3'))
            basemod.append(x.upper().replace('o', '0').replace('l', '1').replace('a', '4').replace('e', '3').replace('s', '$'))
            basemod.append(x.upper().replace('o', '0').replace('l', '1').replace('a', '@').replace('e', '3').replace('s', '$'))
            basemod.append(x.upper().replace('o', '0').replace('l', '!').replace('a', '4').replace('e', '3').replace('s', '$'))
            basemod.append(x.upper().replace('o', '0').replace('l', '!').replace('a', '@').replace('e', '3').replace('s', '$'))

        #perform substitution on baseword combinations
        for x in basemod_append_words:
            basemod.append(x.replace('o', '0'))
            basemod.append(x.replace('a', '4'))
            basemod.append(x.replace('a', '@'))
            basemod.append(x.replace('l', '1'))
            basemod.append(x.replace('l', '!'))
            basemod.append(x.replace('i', '1'))
            basemod.append(x.replace('i', '!'))
            basemod.append(x.replace('e', '3'))
            basemod.append(x.replace('s', '$'))
            basemod.append(x.replace('a', '@').replace('i', '!'))
            basemod.append(x.replace('a', '@').replace('i', '1'))
            basemod.append(x.replace('s', '$').replace('e', '3'))
            basemod.append(x.replace('o', '0').replace('e', '3'))
            basemod.append(x.replace('o', '0').replace('l', '1').replace('e', '3'))
            basemod.append(x.replace('o', '0').replace('l', '!').replace('e', '3'))
            basemod.append(x.replace('o', '0').replace('i', '1').replace('e', '3'))
            basemod.append(x.replace('o', '0').replace('i', '!').replace('e', '3'))
            basemod.append(x.replace('o', '0').replace('l', '1').replace('a', '4').replace('e', '3'))
            basemod.append(x.replace('o', '0').replace('l', '1').replace('a', '@').replace('e', '3'))
            basemod.append(x.replace('o', '0').replace('l', '!').replace('a', '4').replace('e', '3'))
            basemod.append(x.replace('o', '0').replace('l', '!').replace('a', '@').replace('e', '3'))
            basemod.append(x.replace('o', '0').replace('l', '1').replace('a', '4').replace('e', '3').replace('s', '$'))
            basemod.append(x.replace('o', '0').replace('l', '1').replace('a', '@').replace('e', '3').replace('s', '$'))
            basemod.append(x.replace('o', '0').replace('l', '!').replace('a', '4').replace('e', '3').replace('s', '$'))
            basemod.append(x.replace('o', '0').replace('l', '!').replace('a', '@').replace('e', '3').replace('s', '$'))

    #Dedup and write to file
    tmp = []
    openFile = open(outfile, 'a')
    for pwd in basemod:
        if pwd not in tmp:
            tmp.append(pwd)
            openFile.write("{}\n".format(pwd))
    openFile.close()
    print("\n[+] Password list created: {}\n".format(outfile))

if __name__ == '__main__':
    VERSION = "0.0.1"
    main()
