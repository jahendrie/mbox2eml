#!/usr/bin/env python3
#===============================================================================
#   mbox2eml.py     |   version 0.8     |   zlib license    |   2020-02-09
#   James Hendrie   |   hendrie.james@gmail.com
#
#   Script that splits an mbox file into a bunch of eml files.
#===============================================================================
import sys, os
import base64

gOpts = { "verbose" : True }


def print_usage():
    print( "Usage:  mbox2eml.py MBOX_FILE [output_directory]" )


def print_help():
    print("This script will split an mbox format file into a bunch of separate")
    print( "eml format files.  By default, it will also try to guess at the" )
    print( "subject, too, naming the output files as best it can." )

class Email:
    def __init__( self, linesOfText=[] ):
        self.lines = linesOfText
        self.byteString = self.byte_string( self.lines )
        self.subject = self.get_subject()

    def decode_subject( self, subject ):
        b = "=?utf-8?b?"
        ab = "?us-ascii?b?"
        q = "=?utf-8?q?"
        aq = "=?us-ascii?q?"
        endTok = bytes( "?=", "utf-8" )

        for bTok in ( '?b?', '?B?' ):
            tok = bytes( bTok, "utf-8" )
            if tok in subject[:20]:
                sub = subject.partition( tok )[2].partition( endTok )[0]
                return( base64.decodebytes( sub ))

        for qTok in ( '?q?', '?Q?' ):
            tok = bytes( qTok, "utf-8" )
            if tok in subject[:20]:
                sub = subject.partition(tok)[2].partition( endTok )[0].decode()
                return( sub.replace( '_', ' ', -1 ))

    def byte_string( self, lines ):

        s = bytes( "", "utf-8" )
        for bo in lines:
            s += bo

        return( s )


    def get_subject( self ):

        email = self.byteString

        idx = email.find( bytes( "Subject: ", "utf-8" ))
        end = email.find( bytes( "\n", "utf-8"), idx )
        subject = email[ idx : end ]

        while subject.strip() == "":
            start = end
            idx = email.find( bytes( "Subject: ", "utf-8" ), start )
            end = email.find( bytes( "\n", "utf-8"), idx )
            subject = email[ idx : end ]

        annoying = "=?utf-8?"
        aAnnoying = "=?us-ascii?"
        for a in ( annoying, annoying.upper(), aAnnoying, aAnnoying.upper() ):
            if bytes( a, "utf-8" ) in subject:
                subject = self.decode_subject( subject )
                break

        if type( subject ) == type( bytes() ):
            try:
                subStr = subject.decode()
            except UnicodeDecodeError:
                subStr = "_INVALID-SUBJECT_"
        else:
            subStr = subject

        if subStr != "" and subStr != None:
            final = subStr.replace( "Subject: ", '', -1 )
            final = final.replace( '/', '', -1 )
            return( final )

        return( "_NO-SUBJECT_" )


class MBox:

    def __init__( self, mboxPath = "" ):
        self.emails = []

    def emails_from_path( self, mboxPath ):

        io = open( mboxPath, "rb" )
        lines = io.readlines()
        io.close()

        starts = []
        idx = 0
        while idx < len( lines ):
            if bytes( "Delivered-To:", "utf-8" ) in lines[ idx ]:
                starts.append( idx - 1 )
            idx += 1


        count = 0
        num = len( starts )
        pad = len( str( num))
        for s in starts:
            idx = starts.index( s )
            if gOpts[ "verbose" ]:
                count += 1
                print( "Extracting %0*d / %0*d\tfrom '%s'"
                        % ( pad, count, pad, num, mboxPath))
            if idx < len( starts ) - 1:
                self.emails.append( Email( lines[ s : starts[ idx + 1 ] ] ))
            else:
                self.emails.append( Email( lines[ s : ] ))


    def split( self, mbox, outputDir ):


        self.emails_from_path( mbox )

        bookmark = os.getcwd()
        os.chdir( outputDir )

        numEmails = len( self.emails )
        pad = len( str( numEmails ))
        count = 1
        for e in self.emails:

            if gOpts[ "verbose" ]:
                print( "Writing %0*d / %0*d\tinto directory '%s'" %
                        ( pad, count, pad, numEmails, outputDir ))

            fileName = "%0*d_%s.eml" % ( pad, count, e.subject )
            of = open( fileName, 'wb' )
            of.write( e.byteString )
            of.close()

            count += 1

        os.chdir( bookmark )


def new_dir( path ):
    try:
        os.mkdir( path )
        return( True )
    except ( OSError, PermissionError ):
        return( False )


def dir_stuff( path ):
    if not os.path.exists( path ):
        if not new_dir( path ):
            print( "Uh-oh!" )
            sys.exit( 1 )
def main():
    ##  See if they're using the correct number of arguments
    if len( sys.argv ) < 2:
        print_usage()
        sys.exit( 1 )

    if len( sys.argv ) < 3:

        if sys.argv[1] == "-h" or sys.argv[1] == "--help":
            print_usage()
            print( "" )
            print_help()
            sys.exit( 0 )

        d = "%s.d" % sys.argv[1]
        dir_stuff( d )
        mbox = MBox()
        mbox.split( sys.argv[1], d )

    else:
        d = sys.argv[2]
        dir_stuff( d )
        mbox = MBox()
        mbox.split( sys.argv[1], d )

    print( "\nAll done!" )

if __name__ == "__main__":
    main()
